package com.autorun.service;

import com.autorun.config.ConflictException;
import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.ExecutionLog;
import com.autorun.model.ExecutionStatus;
import com.autorun.model.FileType;
import com.autorun.model.Script;
import com.autorun.model.ScriptJob;
import com.autorun.model.TriggerType;
import com.autorun.model.User;
import com.autorun.repository.ExecutionLogRepository;
import com.autorun.repository.ScriptJobRepository;
import com.autorun.repository.ScriptRepository;
import com.autorun.util.ArgumentResolver;
import com.autorun.util.JsonUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArraySet;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

@Service
public class ExecutionService {

    private static final Logger log = LoggerFactory.getLogger(ExecutionService.class);

    private final ExecutionLogRepository executionLogRepository;
    private final ScriptRepository scriptRepository;
    private final ScriptJobRepository jobRepository;
    private final StorageService storageService;
    private final NotificationService notificationService;
    private final String pythonInterpreter;
    private final int maxConcurrent;
    private final int defaultTimeoutSeconds;

    private final Map<Long, Process> runningProcesses = new ConcurrentHashMap<>();
    private final Map<Long, Set<SseEmitter>> emitters = new ConcurrentHashMap<>();
    private final Map<Long, AtomicBoolean> cancelFlags = new ConcurrentHashMap<>();

    public ExecutionService(ExecutionLogRepository executionLogRepository,
                            ScriptRepository scriptRepository,
                            ScriptJobRepository jobRepository,
                            StorageService storageService,
                            NotificationService notificationService,
                            @Value("${autorun.python-interpreter}") String pythonInterpreter,
                            @Value("${autorun.max-concurrent-executions}") int maxConcurrent,
                            @Value("${autorun.default-timeout-seconds}") int defaultTimeoutSeconds) {
        this.executionLogRepository = executionLogRepository;
        this.scriptRepository = scriptRepository;
        this.jobRepository = jobRepository;
        this.storageService = storageService;
        this.notificationService = notificationService;
        this.pythonInterpreter = pythonInterpreter;
        this.maxConcurrent = maxConcurrent;
        this.defaultTimeoutSeconds = defaultTimeoutSeconds;
    }

    /**
     * Runs a script asynchronously. Returns the RUNNING execution record immediately;
     * actual process work happens on a background thread.
     */
    @Transactional
    public ExecutionLog execute(Script script,
                                Map<String, String> arguments,
                                Map<String, String> env,
                                Integer timeoutSeconds,
                                String notifyOn,
                                TriggerType triggeredBy,
                                User user,
                                ScriptJob job) {
        if (runningProcesses.size() >= maxConcurrent) {
            throw new ConflictException("Max concurrent executions reached (%d)".formatted(maxConcurrent));
        }

        List<String> positionalArgs = ArgumentResolver.resolveArguments(
                JsonUtil.parseParams(script.getParametersJson()),
                arguments,
                null);

        ExecutionLog exec = new ExecutionLog();
        exec.setScript(script);
        exec.setTriggeredBy(triggeredBy);
        exec.setUser(user);
        exec.setJob(job);
        exec.setStatus(ExecutionStatus.RUNNING);
        exec.setNotifyOn(notifyOn == null ? "FAILURE" : notifyOn);
        exec.setArgumentsJson(JsonUtil.toJson(ArgumentResolver.nonBlankValues(arguments)));
        exec = executionLogRepository.save(exec);
        final Long executionId = exec.getId();

        String logFileName = "execution-" + executionId + ".log";
        exec.setLogFile(logFileName);
        executionLogRepository.save(exec);

        final ExecutionLog persisted = exec;
        final int timeout = timeoutSeconds == null || timeoutSeconds <= 0 ? defaultTimeoutSeconds : timeoutSeconds;
        final LocalDateTime started = LocalDateTime.now();

        Thread worker = new Thread(() -> runProcess(executionId, script, positionalArgs, env, timeout,
                started, logFileName, persisted.getNotifyOn()), "exec-" + executionId);
        worker.setDaemon(true);
        worker.start();
        return persisted;
    }

    private void runProcess(Long executionId, Script script, List<String> positionalArgs,
                            Map<String, String> env, int timeout,
                            LocalDateTime started, String logFileName, String notifyOn) {
        StringBuilder buffer = new StringBuilder();
        AtomicBoolean cancelRequested = new AtomicBoolean(false);
        cancelFlags.put(executionId, cancelRequested);

        Process process = null;
        ExecutionStatus finalStatus = ExecutionStatus.FAILED;
        Integer exitCode = null;
        String errorMessage = null;

        try {
            List<String> command = buildCommand(script, positionalArgs);
            ProcessBuilder pb = new ProcessBuilder(command);
            pb.directory(storageService.getScriptDir().toFile());
            if (env != null) {
                pb.environment().putAll(env);
            }
            append(buffer, logFileName, "== command: " + String.join(" ", command));
            append(buffer, logFileName, "== started at " + started.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));

            process = pb.start();
            runningProcesses.put(executionId, process);

            Thread stdout = readStream(process, false, executionId, buffer, logFileName);
            Thread stderr = readStream(process, true, executionId, buffer, logFileName);
            stdout.start();
            stderr.start();

            boolean finished = process.waitFor(timeout, TimeUnit.SECONDS);
            stdout.join(2000);
            stderr.join(2000);

            if (!finished) {
                process.destroyForcibly();
                finalStatus = ExecutionStatus.TIMEOUT;
                append(buffer, logFileName, "== TIMEOUT after " + timeout + "s, process killed");
            } else {
                exitCode = process.exitValue();
                finalStatus = exitCode == 0 ? ExecutionStatus.SUCCESS : ExecutionStatus.FAILED;
            }
        } catch (IOException e) {
            finalStatus = ExecutionStatus.FAILED;
            errorMessage = "Failed to launch process: " + e.getMessage();
            append(buffer, logFileName, "== ERROR: " + errorMessage);
        } catch (Exception e) {
            finalStatus = ExecutionStatus.FAILED;
            errorMessage = e.getMessage();
            append(buffer, logFileName, "== ERROR: " + errorMessage);
        } finally {
            if (cancelRequested.get()) {
                finalStatus = ExecutionStatus.CANCELLED;
                append(buffer, logFileName, "== CANCELLED by user");
            }
            if (process != null) {
                process.destroy();
            }
            runningProcesses.remove(executionId);
            cancelFlags.remove(executionId);

            ExecutionLog exec = executionLogRepository.findById(executionId).orElse(null);
            if (exec != null) {
                exec.setStatus(finalStatus);
                exec.setExitCode(exitCode);
                exec.setFinishedAt(LocalDateTime.now());
                exec.setDurationMs(java.time.Duration.between(started, LocalDateTime.now()).toMillis());
                exec.setLogContent(buffer.toString());
                exec.setErrorMessage(errorMessage);
                executionLogRepository.save(exec);
                append(buffer, logFileName, "== finished: " + finalStatus
                        + " (exit " + exitCode + ") in " + exec.getDurationMs() + " ms");

                script.setLastExecutedAt(LocalDateTime.now());
                scriptRepository.save(script);

                notificationService.notifyExecution(exec, notifyOn);
            }
            broadcastStatus(executionId, finalStatus, exitCode);
            completeEmitters(executionId, finalStatus, exitCode);
        }
    }

    private List<String> buildCommand(Script script, List<String> positionalArgs) {
        List<String> cmd = new ArrayList<>();
        String path = script.getStoragePath() != null
                ? script.getStoragePath()
                : storageService.scriptPath(script.getFilename()).toString();
        switch (script.getFileType()) {
            case PY -> {
                cmd.add(pythonInterpreter);
                cmd.add(path);
            }
            case SH -> {
                cmd.add("bash");
                cmd.add(path);
            }
            case PS1 -> {
                cmd.addAll(List.of("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path));
            }
            case BAT, CMD -> {
                cmd.addAll(List.of("cmd", "/c", path));
            }
        }
        cmd.addAll(positionalArgs);
        return cmd;
    }

    private Thread readStream(Process process, boolean isError, Long executionId,
                              StringBuilder buffer, String logFileName) {
        return new Thread(() -> {
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                    isError ? process.getErrorStream() : process.getInputStream(),
                    StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    append(buffer, logFileName,
                            (isError ? "[stderr] " : "") + line);
                    broadcast(executionId, "log",
                            "{\"line\": \"%s\", \"stream\": \"%s\"}"
                                    .formatted(escape(line), isError ? "stderr" : "stdout"));
                }
            } catch (IOException ignored) {
                // stream closed when process dies
            }
        });
    }

    private synchronized void append(StringBuilder buffer, String logFileName, String line) {
        buffer.append(line).append('\n');
        try {
            storageService.appendLog(logFileName, line + System.lineSeparator());
        } catch (Exception ignored) {
            // file logging must never break execution
        }
    }

    public String getLog(Long executionId, Integer tail) {
        ExecutionLog exec = get(executionId);
        String content = storageService.readLogContent(exec.getLogFile());
        if (content.isBlank() && exec.getLogContent() != null) {
            content = exec.getLogContent();
        }
        if (tail == null || tail <= 0) {
            return content;
        }
        List<String> lines = content.lines().toList();
        return String.join(System.lineSeparator(), lines.subList(Math.max(0, lines.size() - tail), lines.size()));
    }

    public ExecutionLog get(Long executionId) {
        return executionLogRepository.findById(executionId)
                .orElseThrow(() -> new ResourceNotFoundException("Execution not found: " + executionId));
    }

    public List<ExecutionLog> list(Long scriptId, ExecutionStatus status, User user) {
        List<ExecutionLog> all = executionLogRepository.findAll();
        List<ExecutionLog> result = new ArrayList<>(all);
        if (scriptId != null) {
            result.removeIf(e -> e.getScript() == null || !e.getScript().getId().equals(scriptId));
        }
        if (status != null) {
            result.removeIf(e -> e.getStatus() != status);
        }
        if (user != null && !"ADMIN".equals(user.getRole().name())) {
            result.removeIf(e -> e.getUser() == null || !e.getUser().getId().equals(user.getId()));
        }
        result.sort((a, b) -> b.getStartedAt().compareTo(a.getStartedAt()));
        return result;
    }

    /**
     * Entry point invoked by the Quartz job executor when a scheduled job fires.
     */
    @Transactional
    public void runScheduledJob(Long jobId) {
        ScriptJob job = jobRepository.findById(jobId).orElse(null);
        if (job == null || !job.isEnabled() || job.getStatus() != com.autorun.model.JobStatus.SCHEDULED) {
            log.warn("Scheduled job {} not runnable; skipping", jobId);
            return;
        }
        if (job.getScript() == null) {
            log.warn("Scheduled job {} has no script; skipping", jobId);
            return;
        }
        job.setLastRunAt(LocalDateTime.now());
        jobRepository.save(job);
        execute(job.getScript(),
                JsonUtil.parseArguments(job.getArgumentsJson()),
                Map.of(),
                null,
                job.getNotifyOn(),
                TriggerType.SCHEDULED,
                job.getCreatedBy(),
                job);
    }

    public void cancel(Long executionId) {        ExecutionLog exec = get(executionId);
        if (exec.getStatus() != ExecutionStatus.RUNNING) {
            throw new ConflictException("Execution is not running (current status: " + exec.getStatus() + ")");
        }
        AtomicBoolean flag = cancelFlags.computeIfAbsent(executionId, k -> new AtomicBoolean());
        flag.set(true);
        Process p = runningProcesses.get(executionId);
        if (p != null) {
            p.destroyForcibly();
        }
    }

    public long runningCount() {
        return runningProcesses.size();
    }

    // ----- SSE support -----

    public SseEmitter stream(Long executionId) {
        SseEmitter emitter = new SseEmitter(0L);
        ExecutionLog exec = get(executionId);
        if (exec.getStatus() != ExecutionStatus.RUNNING) {
            complete(emitter, exec.getStatus(), exec.getExitCode());
            return emitter;
        }
        emitters.computeIfAbsent(executionId, k -> new CopyOnWriteArraySet<>()).add(emitter);
        emitter.onCompletion(() -> removeEmitter(executionId, emitter));
        emitter.onTimeout(() -> removeEmitter(executionId, emitter));
        emitter.onError(e -> removeEmitter(executionId, emitter));
        return emitter;
    }

    private void broadcast(Long executionId, String name, String data) {
        Set<SseEmitter> set = emitters.get(executionId);
        if (set == null) {
            return;
        }
        for (SseEmitter emitter : set) {
            try {
                emitter.send(SseEmitter.event().name(name).data(data));
            } catch (IOException e) {
                removeEmitter(executionId, emitter);
            }
        }
    }

    private void broadcastStatus(Long executionId, ExecutionStatus status, Integer exitCode) {
        broadcast(executionId, "status",
                "{\"status\": \"%s\", \"exitCode\": %s}".formatted(status, exitCode == null ? "null" : exitCode));
    }

    private void completeEmitters(Long executionId, ExecutionStatus status, Integer exitCode) {
        Set<SseEmitter> set = emitters.remove(executionId);
        if (set == null) {
            return;
        }
        for (SseEmitter emitter : set) {
            complete(emitter, status, exitCode);
        }
    }

    private void complete(SseEmitter emitter, ExecutionStatus status, Integer exitCode) {
        try {
            emitter.send(SseEmitter.event().name("complete")
                    .data("{\"status\": \"%s\", \"exitCode\": %s}".formatted(status, exitCode == null ? "null" : exitCode)));
        } catch (IOException ignored) {
        }
        emitter.complete();
    }

    private void removeEmitter(Long executionId, SseEmitter emitter) {
        Set<SseEmitter> set = emitters.get(executionId);
        if (set != null) {
            set.remove(emitter);
        }
    }

    private String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
