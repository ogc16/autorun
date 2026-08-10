package com.autorun.controller;

import com.autorun.model.ScriptJob;
import com.autorun.model.User;
import com.autorun.security.AppUserDetails;
import com.autorun.service.AuditService;
import com.autorun.service.JobService;
import com.autorun.service.ScriptService;
import com.autorun.service.UserService;
import com.autorun.util.JsonUtil;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/jobs")
public class JobApiController {

    private final JobService jobService;
    private final ScriptService scriptService;
    private final UserService userService;
    private final AuditService auditService;

    public JobApiController(JobService jobService, ScriptService scriptService,
                            UserService userService, AuditService auditService) {
        this.jobService = jobService;
        this.scriptService = scriptService;
        this.userService = userService;
        this.auditService = auditService;
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<ScriptJob> create(@RequestBody JobRequest request,
                                            Authentication authentication,
                                            HttpServletRequest http) {
        User user = currentUser(authentication);
        ScriptJob job = jobService.create(user, toJob(request, new ScriptJob()));
        auditService.record(user, "JOB_CREATED", "JOB", job.getId().toString(),
                "Created scheduled job '" + job.getName() + "'", http);
        return ResponseEntity.status(HttpStatus.CREATED).body(job);
    }

    @GetMapping
    public List<ScriptJob> list() {
        return jobService.list();
    }

    @GetMapping("/preview")
    public Map<String, Object> preview(@RequestParam("cron") String cron,
                                       @RequestParam(defaultValue = "UTC") String timeZone,
                                       @RequestParam(defaultValue = "5") int count) {
        return jobService.preview(cron, timeZone, count);
    }

    @GetMapping("/{id}")
    public ScriptJob get(@PathVariable Long id) {
        return jobService.get(id);
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ScriptJob update(@PathVariable Long id, @RequestBody JobRequest request,
                            Authentication authentication, HttpServletRequest http) {
        User user = currentUser(authentication);
        ScriptJob job = jobService.update(id, toJob(request, new ScriptJob()));
        auditService.record(user, "JOB_UPDATED", "JOB", id.toString(),
                "Updated scheduled job '" + job.getName() + "'", http);
        return job;
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void delete(@PathVariable Long id, Authentication authentication, HttpServletRequest http) {
        User user = currentUser(authentication);
        ScriptJob job = jobService.get(id);
        jobService.delete(id);
        auditService.record(user, "JOB_DELETED", "JOB", id.toString(),
                "Deleted scheduled job '" + job.getName() + "'", http);
    }

    @PostMapping("/{id}/pause")
    @PreAuthorize("hasRole('ADMIN')")
    public ScriptJob pause(@PathVariable Long id, Authentication authentication, HttpServletRequest http) {
        User user = currentUser(authentication);
        ScriptJob job = jobService.pause(id);
        auditService.record(user, "JOB_PAUSED", "JOB", id.toString(), "Paused job '" + job.getName() + "'", http);
        return job;
    }

    @PostMapping("/{id}/resume")
    @PreAuthorize("hasRole('ADMIN')")
    public ScriptJob resume(@PathVariable Long id, Authentication authentication, HttpServletRequest http) {
        User user = currentUser(authentication);
        ScriptJob job = jobService.resume(id);
        auditService.record(user, "JOB_RESUMED", "JOB", id.toString(), "Resumed job '" + job.getName() + "'", http);
        return job;
    }

    @PostMapping("/{id}/run-now")
    public ScriptJob runNow(@PathVariable Long id, Authentication authentication, HttpServletRequest http) {
        User user = currentUser(authentication);
        ScriptJob job = jobService.runNow(id);
        auditService.record(user, "JOB_RUN_NOW", "JOB", id.toString(),
                "Triggered immediate run of job '" + job.getName() + "'", http);
        return job;
    }

    private ScriptJob toJob(JobRequest request, ScriptJob job) {
        job.setName(request.name());
        job.setDescription(request.description());
        if (request.scriptId() != null) {
            job.setScript(scriptService.get(request.scriptId()));
        }
        job.setCronExpression(request.cronExpression());
        job.setTimeZone(request.timeZone() == null ? "UTC" : request.timeZone());
        job.setArgumentsJson(JsonUtil.toJson(request.arguments()));
        job.setNotifyOn(request.notifyOn() == null ? "FAILURE" : request.notifyOn());
        return job;
    }

    private User currentUser(Authentication authentication) {
        AppUserDetails principal = (AppUserDetails) authentication.getPrincipal();
        return userService.get(principal.getId());
    }

    public record JobRequest(String name, String description, Long scriptId, String cronExpression,
                             String timeZone, Map<String, String> arguments, String notifyOn) {
    }
}
