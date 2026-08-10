package com.autorun.service;

import com.autorun.config.ConflictException;
import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.JobStatus;
import com.autorun.model.ScriptJob;
import com.autorun.model.User;
import com.autorun.repository.ScriptJobRepository;
import com.autorun.repository.ScriptRepository;
import com.autorun.util.JsonUtil;
import org.quartz.CronExpression;
import org.quartz.CronScheduleBuilder;
import org.quartz.CronTrigger;
import org.quartz.JobBuilder;
import org.quartz.JobDataMap;
import org.quartz.JobDetail;
import org.quartz.JobKey;
import org.quartz.Scheduler;
import org.quartz.SchedulerException;
import org.quartz.TriggerBuilder;
import org.quartz.TriggerKey;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.text.ParseException;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;

@Service
public class JobService {

    private static final Logger log = LoggerFactory.getLogger(JobService.class);
    private static final String GROUP = "autorun-jobs";

    private final Scheduler scheduler;
    private final ScriptJobRepository jobRepository;
    private final ScriptRepository scriptRepository;

    public JobService(Scheduler scheduler,
                      ScriptJobRepository jobRepository,
                      ScriptRepository scriptRepository) {
        this.scheduler = scheduler;
        this.jobRepository = jobRepository;
        this.scriptRepository = scriptRepository;
    }

    @Transactional
    public ScriptJob create(User user, ScriptJob draft) {
        validate(draft);
        if (jobRepository.existsByName(draft.getName())) {
            throw new ConflictException("A job named '%s' already exists".formatted(draft.getName()));
        }
        draft.setCreatedBy(user);
        draft.setStatus(JobStatus.SCHEDULED);
        draft.setEnabled(true);
        draft.setCreatedAt(LocalDateTime.now());
        ScriptJob saved = jobRepository.save(draft);
        scheduleQuartz(saved);
        return saved;
    }

    @Transactional
    public ScriptJob update(Long id, ScriptJob updates) {
        ScriptJob job = get(id);
        if (updates.getName() != null && !updates.getName().isBlank()) {
            if (!job.getName().equals(updates.getName()) && jobRepository.existsByName(updates.getName())) {
                throw new ConflictException("A job named '%s' already exists".formatted(updates.getName()));
            }
            job.setName(updates.getName());
        }
        if (updates.getDescription() != null) {
            job.setDescription(updates.getDescription());
        }
        if (updates.getCronExpression() != null && !updates.getCronExpression().isBlank()) {
            validateCron(updates.getCronExpression());
            job.setCronExpression(updates.getCronExpression());
        }
        if (updates.getTimeZone() != null && !updates.getTimeZone().isBlank()) {
            job.setTimeZone(updates.getTimeZone());
        }
        if (updates.getArgumentsJson() != null) {
            job.setArgumentsJson(updates.getArgumentsJson());
        }
        if (updates.getNotifyOn() != null) {
            job.setNotifyOn(updates.getNotifyOn());
        }
        jobRepository.save(job);
        scheduleQuartz(job);
        return job;
    }

    @Transactional
    public void delete(Long id) {
        ScriptJob job = get(id);
        removeQuartz(id);
        jobRepository.delete(job);
    }

    @Transactional
    public ScriptJob pause(Long id) {
        ScriptJob job = get(id);
        job.setStatus(JobStatus.PAUSED);
        jobRepository.save(job);
        try {
            scheduler.pauseJob(jobKey(id));
        } catch (SchedulerException e) {
            log.warn("Failed to pause Quartz job {}", id, e);
        }
        return job;
    }

    @Transactional
    public ScriptJob resume(Long id) {
        ScriptJob job = get(id);
        job.setStatus(JobStatus.SCHEDULED);
        jobRepository.save(job);
        try {
            scheduler.resumeJob(jobKey(id));
        } catch (SchedulerException e) {
            log.warn("Failed to resume Quartz job {}", id, e);
        }
        return job;
    }

    @Transactional
    public ScriptJob runNow(Long id) {
        ScriptJob job = get(id);
        try {
            scheduler.triggerJob(jobKey(id));
        } catch (SchedulerException e) {
            throw new IllegalStateException("Failed to trigger job immediately", e);
        }
        return job;
    }

    public List<ScriptJob> list() {
        List<ScriptJob> jobs = jobRepository.findAll();
        jobs.forEach(this::attachNextFireTime);
        jobs.sort((a, b) -> a.getName().compareToIgnoreCase(b.getName()));
        return jobs;
    }

    public ScriptJob get(Long id) {
        ScriptJob job = jobRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Job not found: " + id));
        attachNextFireTime(job);
        return job;
    }

    public Map<String, Object> preview(String cron, String timeZone, int count) {
        try {
            CronExpression expression = new CronExpression(cron);
            if (timeZone != null && !timeZone.isBlank()) {
                expression.setTimeZone(TimeZone.getTimeZone(timeZone));
            }
            Date cursor = new Date();
            List<String> times = new ArrayList<>();
            for (int i = 0; i < count; i++) {
                cursor = expression.getNextValidTimeAfter(cursor);
                if (cursor == null) {
                    break;
                }
                times.add(cursor.toInstant().toString());
            }
            return Map.of(
                    "cron", cron,
                    "timeZone", timeZone == null ? "UTC" : timeZone,
                    "nextFireTimes", times);
        } catch (ParseException e) {
            throw new IllegalArgumentException("Invalid cron expression: " + cron);
        }
    }

    // ----- Quartz wiring -----

    private void scheduleQuartz(ScriptJob job) {
        JobDataMap data = new JobDataMap();
        data.put("jobId", job.getId());
        JobDetail detail = JobBuilder.newJob(ScheduledJobExecutor.class)
                .withIdentity(jobKey(job.getId()))
                .usingJobData(data)
                .storeDurably()
                .build();

        CronTrigger trigger = TriggerBuilder.newTrigger()
                .withIdentity(triggerKey(job.getId()))
                .forJob(detail)
                .withSchedule(CronScheduleBuilder.cronSchedule(job.getCronExpression())
                        .inTimeZone(TimeZone.getTimeZone(job.getTimeZone() == null ? "UTC" : job.getTimeZone())))
                .build();

        try {
            if (scheduler.checkExists(jobKey(job.getId()))) {
                scheduler.rescheduleJob(triggerKey(job.getId()), trigger);
            } else {
                scheduler.scheduleJob(detail, trigger);
            }
            if (job.getStatus() == JobStatus.PAUSED) {
                scheduler.pauseJob(jobKey(job.getId()));
            }
            scheduler.start();
        } catch (SchedulerException e) {
            throw new IllegalStateException("Failed to schedule Quartz job", e);
        }
    }

    private void removeQuartz(Long jobId) {
        try {
            scheduler.unscheduleJob(triggerKey(jobId));
            scheduler.deleteJob(jobKey(jobId));
        } catch (SchedulerException e) {
            log.warn("Failed to remove Quartz job {}", jobId, e);
        }
    }

    private void attachNextFireTime(ScriptJob job) {
        try {
            TriggerKey tk = triggerKey(job.getId());
            CronTrigger trigger = (CronTrigger) scheduler.getTrigger(tk);
            if (trigger != null && job.getStatus() == JobStatus.SCHEDULED) {
                Date next = trigger.getFireTimeAfter(new Date());
                if (next != null) {
                    job.setNextFireTimeForView(LocalDateTime.ofInstant(next.toInstant(),
                            ZoneId.of(job.getTimeZone() == null ? "UTC" : job.getTimeZone())));
                }
            }
        } catch (SchedulerException e) {
            log.warn("Failed to read next fire time for job {}", job.getId(), e);
        }
    }

    private JobKey jobKey(Long id) {
        return JobKey.jobKey("job-" + id, GROUP);
    }

    private TriggerKey triggerKey(Long id) {
        return TriggerKey.triggerKey("trigger-" + id, GROUP);
    }

    private void validate(ScriptJob job) {
        if (job.getName() == null || job.getName().isBlank()) {
            throw new IllegalArgumentException("Job name is required");
        }
        if (job.getScript() == null || job.getScript().getId() == null
                || !scriptRepository.existsById(job.getScript().getId())) {
            throw new IllegalArgumentException("A valid script is required");
        }
        validateCron(job.getCronExpression());
    }

    private void validateCron(String cron) {
        if (cron == null || cron.isBlank()) {
            throw new IllegalArgumentException("Cron expression is required");
        }
        if (!CronExpression.isValidExpression(cron)) {
            throw new IllegalArgumentException("Invalid cron expression: " + cron);
        }
    }

    public List<ScriptJob> findByScriptId(Long scriptId) {
        return jobRepository.findByScriptId(scriptId);
    }
}
