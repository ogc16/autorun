package com.autorun.controller;

import com.autorun.model.ScriptJob;
import com.autorun.model.User;
import com.autorun.repository.ScriptRepository;
import com.autorun.service.AuditService;
import com.autorun.service.JobService;
import com.autorun.service.UserService;
import com.autorun.util.JsonUtil;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.util.Map;

@Controller
@RequestMapping("/jobs")
public class JobViewController extends BaseViewController {

    private final JobService jobService;
    private final ScriptRepository scriptRepository;
    private final AuditService auditService;

    public JobViewController(UserService userService,
                             JobService jobService,
                             ScriptRepository scriptRepository,
                             AuditService auditService) {
        super(userService);
        this.jobService = jobService;
        this.scriptRepository = scriptRepository;
        this.auditService = auditService;
    }

    @GetMapping
    public String list(Model model) {
        model.addAttribute("jobs", jobService.list());
        return "jobs";
    }

    @GetMapping("/new")
    public String newForm(Model model) {
        model.addAttribute("job", new ScriptJob());
        model.addAttribute("scripts", scriptRepository.findAll());
        model.addAttribute("mode", "create");
        return "job-form";
    }

    @PostMapping("/new")
    public String create(@RequestParam("name") String name,
                         @RequestParam(required = false) String description,
                         @RequestParam("scriptId") Long scriptId,
                         @RequestParam("cronExpression") String cronExpression,
                         @RequestParam(defaultValue = "UTC") String timeZone,
                         @RequestParam(required = false) String argumentsJson,
                         @RequestParam(defaultValue = "FAILURE") String notifyOn,
                         Authentication authentication,
                         RedirectAttributes redirect,
                         HttpServletRequest http) {
        User user = currentUser(authentication);
        try {
            ScriptJob job = new ScriptJob();
            job.setName(name);
            job.setDescription(description);
            job.setScript(scriptRepository.findById(scriptId)
                    .orElseThrow(() -> new IllegalArgumentException("Unknown script")));
            job.setCronExpression(cronExpression);
            job.setTimeZone(timeZone);
            job.setArgumentsJson(argumentsJson);
            job.setNotifyOn(notifyOn);
            ScriptJob saved = jobService.create(user, job);
            auditService.record(user, "JOB_CREATED", "JOB", saved.getId().toString(),
                    "Created scheduled job '" + saved.getName() + "'", http);
            redirect.addFlashAttribute("flashSuccess", "Job scheduled successfully");
            return "redirect:/jobs";
        } catch (Exception e) {
            redirect.addFlashAttribute("flashError", e.getMessage());
            return "redirect:/jobs/new";
        }
    }

    @GetMapping("/{id}")
    public String detail(@PathVariable Long id, Model model) {
        model.addAttribute("job", jobService.get(id));
        model.addAttribute("scripts", scriptRepository.findAll());
        return "job-form";
    }

    @PostMapping("/{id}/edit")
    public String edit(@PathVariable Long id,
                       @RequestParam("name") String name,
                       @RequestParam(required = false) String description,
                       @RequestParam("scriptId") Long scriptId,
                       @RequestParam("cronExpression") String cronExpression,
                       @RequestParam(defaultValue = "UTC") String timeZone,
                       @RequestParam(required = false) String argumentsJson,
                       @RequestParam(defaultValue = "FAILURE") String notifyOn,
                       Authentication authentication,
                       RedirectAttributes redirect,
                       HttpServletRequest http) {
        User user = currentUser(authentication);
        try {
            ScriptJob updates = new ScriptJob();
            updates.setName(name);
            updates.setDescription(description);
            updates.setScript(scriptRepository.findById(scriptId).orElse(null));
            updates.setCronExpression(cronExpression);
            updates.setTimeZone(timeZone);
            updates.setArgumentsJson(argumentsJson);
            updates.setNotifyOn(notifyOn);
            ScriptJob job = jobService.update(id, updates);
            auditService.record(user, "JOB_UPDATED", "JOB", id.toString(),
                    "Updated scheduled job '" + job.getName() + "'", http);
            redirect.addFlashAttribute("flashSuccess", "Job updated");
            return "redirect:/jobs";
        } catch (Exception e) {
            redirect.addFlashAttribute("flashError", e.getMessage());
            return "redirect:/jobs/" + id;
        }
    }

    @PostMapping("/{id}/delete")
    public String delete(@PathVariable Long id, Authentication authentication,
                         RedirectAttributes redirect, HttpServletRequest http) {
        User user = currentUser(authentication);
        jobService.delete(id);
        auditService.record(user, "JOB_DELETED", "JOB", id.toString(), "Deleted scheduled job", http);
        redirect.addFlashAttribute("flashSuccess", "Job deleted");
        return "redirect:/jobs";
    }

    @PostMapping("/{id}/pause")
    public String pause(@PathVariable Long id, Authentication authentication,
                        RedirectAttributes redirect, HttpServletRequest http) {
        User user = currentUser(authentication);
        jobService.pause(id);
        auditService.record(user, "JOB_PAUSED", "JOB", id.toString(), "Paused scheduled job", http);
        redirect.addFlashAttribute("flashSuccess", "Job paused");
        return "redirect:/jobs";
    }

    @PostMapping("/{id}/resume")
    public String resume(@PathVariable Long id, Authentication authentication,
                         RedirectAttributes redirect, HttpServletRequest http) {
        User user = currentUser(authentication);
        jobService.resume(id);
        auditService.record(user, "JOB_RESUMED", "JOB", id.toString(), "Resumed scheduled job", http);
        redirect.addFlashAttribute("flashSuccess", "Job resumed");
        return "redirect:/jobs";
    }

    @PostMapping("/{id}/run-now")
    public String runNow(@PathVariable Long id, Authentication authentication,
                         RedirectAttributes redirect, HttpServletRequest http) {
        User user = currentUser(authentication);
        jobService.runNow(id);
        auditService.record(user, "JOB_RUN_NOW", "JOB", id.toString(), "Triggered immediate run", http);
        redirect.addFlashAttribute("flashSuccess", "Job triggered — check Executions");
        return "redirect:/jobs";
    }

    @GetMapping("/preview")
    @ResponseBody
    public ResponseEntity<Map<String, Object>> preview(@RequestParam String cron,
                                                       @RequestParam(defaultValue = "UTC") String timeZone) {
        return ResponseEntity.ok(jobService.preview(cron, timeZone, 5));
    }
}
