package com.autorun.service;

import com.autorun.config.ConflictException;
import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.*;
import com.autorun.repository.ScriptRepository;
import com.autorun.repository.WorkflowExecutionRepository;
import com.autorun.repository.WorkflowRepository;
import com.autorun.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

@Service
public class WorkflowService {

    private static final Logger log = LoggerFactory.getLogger(WorkflowService.class);
    private static final ObjectMapper mapper = new ObjectMapper();

    private final WorkflowRepository workflowRepository;
    private final WorkflowExecutionRepository workflowExecutionRepository;
    private final ExecutionService executionService;
    private final ScriptRepository scriptRepository;
    private final AtomicBoolean cancelFlag = new AtomicBoolean(false);
    private final ConcurrentHashMap<Long, AtomicBoolean> activeCancels = new ConcurrentHashMap<>();

    public WorkflowService(WorkflowRepository workflowRepository,
                           WorkflowExecutionRepository workflowExecutionRepository,
                           ExecutionService executionService,
                           ScriptRepository scriptRepository) {
        this.workflowRepository = workflowRepository;
        this.workflowExecutionRepository = workflowExecutionRepository;
        this.executionService = executionService;
        this.scriptRepository = scriptRepository;
    }

    public List<Workflow> list(String search) {
        if (search != null && !search.isBlank()) {
            return workflowRepository.findByNameContainingIgnoreCaseOrDescriptionContainingIgnoreCase(search, search);
        }
        return workflowRepository.findAll();
    }

    public Workflow get(Long id) {
        return workflowRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Workflow not found: " + id));
    }

    public Workflow create(User user, String name, String description, String tags,
                           List<WorkflowStep> steps, boolean enabled) {
        if (workflowRepository.existsByName(name)) {
            throw new ConflictException("Workflow name already exists: " + name);
        }
        Workflow wf = new Workflow();
        wf.setName(name);
        wf.setDescription(description);
        wf.setTags(tags);
        wf.setStepsJson(JsonUtil.toJson(steps));
        wf.setEnabled(enabled);
        wf.setCreatedBy(user);
        return workflowRepository.save(wf);
    }

    public Workflow update(Long id, String name, String description, String tags,
                           List<WorkflowStep> steps, boolean enabled) {
        Workflow wf = get(id);
        if (name != null) wf.setName(name);
        if (description != null) wf.setDescription(description);
        if (tags != null) wf.setTags(tags);
        if (steps != null)         wf.setStepsJson(JsonUtil.toJson(steps));
        wf.setEnabled(enabled);
        wf.setUpdatedAt(LocalDateTime.now());
        return workflowRepository.save(wf);
    }

    public void delete(Long id) {
        Workflow wf = get(id);
        workflowRepository.delete(wf);
    }

    public List<WorkflowStep> parseSteps(Workflow wf) {
        try {
            return mapper.readValue(wf.getStepsJson(), new TypeReference<>() {});
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse workflow steps: " + e.getMessage());
        }
    }

    public WorkflowExecution runWorkflow(Long workflowId, User user) {
        Workflow wf = get(workflowId);
        if (!wf.isEnabled()) {
            throw new ConflictException("Workflow is disabled: " + wf.getName());
        }

        List<WorkflowStep> steps = parseSteps(wf);
        if (steps.isEmpty()) {
            throw new ConflictException("Workflow has no steps");
        }
        final List<WorkflowStep> finalSteps = steps;

        WorkflowExecution we = new WorkflowExecution();
        we.setWorkflow(wf);
        we.setUser(user);
        we.setStatus(ExecutionStatus.RUNNING);
        we.setTotalSteps(finalSteps.size());
        we.setCurrentStep(0);
        we = workflowExecutionRepository.save(we);
        final WorkflowExecution finalWe = we;

        wf.setLastRunAt(LocalDateTime.now());
        workflowRepository.save(wf);

        AtomicBoolean cancel = new AtomicBoolean(false);
        activeCancels.put(finalWe.getId(), cancel);

        Thread execThread = new Thread(() -> executeSteps(finalWe, finalSteps, cancel));
        execThread.start();

        return finalWe;
    }

    private void executeSteps(WorkflowExecution we, List<WorkflowStep> steps, AtomicBoolean cancel) {
        StringBuilder logBuffer = new StringBuilder();
        logBuffer.append("=== Workflow: ").append(we.getWorkflow().getName()).append(" ===\n");

        for (int i = 0; i < steps.size(); i++) {
            if (cancel.get()) {
                we.setStatus(ExecutionStatus.CANCELLED);
                logBuffer.append("CANCELLED at step ").append(i + 1).append("\n");
                break;
            }

            WorkflowStep step = steps.get(i);
            we.setCurrentStep(i + 1);
            we.setLogContent(logBuffer.toString());
            workflowExecutionRepository.save(we);

            logBuffer.append("\n--- Step ").append(i + 1).append(": ").append(step.getName()).append(" ---\n");

            Script script = scriptRepository.findById(step.getScriptId()).orElse(null);
            if (script == null) {
                logBuffer.append("ERROR: Script not found (ID: ").append(step.getScriptId()).append(")\n");
                if (step.getOnError() == WorkflowStepOnError.STOP) {
                    we.setStatus(ExecutionStatus.FAILED);
                    break;
                }
                continue;
            }

            logBuffer.append("Running: ").append(script.getName()).append("\n");

            try {
                ExecutionLog el = executionService.execute(
                        script, step.getParamsJson() != null ? JsonUtil.parseArguments(step.getParamsJson()) : Map.of(),
                        null, step.getTimeoutSeconds(), "FAILURE",
                        TriggerType.SCHEDULED, we.getUser(), null);

                for (int w = 0; w < step.getTimeoutSeconds() * 10; w++) {
                    if (cancel.get()) break;
                    ExecutionLog current = executionService.get(el.getId());
                    if (current.getStatus() != ExecutionStatus.RUNNING) {
                        logBuffer.append("Status: ").append(current.getStatus()).append("\n");
                        if (current.getExitCode() != null) {
                            logBuffer.append("Exit code: ").append(current.getExitCode()).append("\n");
                        }

                        if (current.getStatus() == ExecutionStatus.FAILED ||
                                current.getStatus() == ExecutionStatus.TIMEOUT) {
                            if (step.getOnError() == WorkflowStepOnError.STOP) {
                                we.setStatus(ExecutionStatus.FAILED);
                                logBuffer.append("STOPPING: step failed and onError=STOP\n");
                                we.setLogContent(logBuffer.toString());
                                we.setFinishedAt(LocalDateTime.now());
                                we.setDurationMs(java.time.Duration.between(we.getStartedAt(), we.getFinishedAt()).toMillis());
                                workflowExecutionRepository.save(we);
                                activeCancels.remove(we.getId());
                                return;
                            } else if (step.getOnError() == WorkflowStepOnError.CONTINUE) {
                                logBuffer.append("CONTINUING: step failed but onError=CONTINUE\n");
                            }
                        }
                        break;
                    }
                    Thread.sleep(100);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                logBuffer.append("Interrupted\n");
            } catch (Exception e) {
                logBuffer.append("Exception: ").append(e.getMessage()).append("\n");
                if (step.getOnError() == WorkflowStepOnError.STOP) {
                    we.setStatus(ExecutionStatus.FAILED);
                    we.setLogContent(logBuffer.toString());
                    we.setFinishedAt(LocalDateTime.now());
                    we.setDurationMs(java.time.Duration.between(we.getStartedAt(), we.getFinishedAt()).toMillis());
                    workflowExecutionRepository.save(we);
                    activeCancels.remove(we.getId());
                    return;
                }
            }
        }

        if (we.getStatus() == ExecutionStatus.RUNNING) {
            we.setStatus(ExecutionStatus.SUCCESS);
        }
        we.setLogContent(logBuffer.toString());
        we.setFinishedAt(LocalDateTime.now());
        we.setDurationMs(java.time.Duration.between(we.getStartedAt(), we.getFinishedAt()).toMillis());
        workflowExecutionRepository.save(we);
        activeCancels.remove(we.getId());
    }

    public void cancel(Long executionId) {
        AtomicBoolean cancel = activeCancels.get(executionId);
        if (cancel != null) {
            cancel.set(true);
        }
    }

    public List<WorkflowExecution> recentExecutions() {
        return workflowExecutionRepository.findTop20ByOrderByStartedAtDesc();
    }

    public WorkflowExecution getExecution(Long id) {
        return workflowExecutionRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Workflow execution not found: " + id));
    }
}
