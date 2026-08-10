package com.autorun.controller;

import com.autorun.model.ExecutionLog;
import com.autorun.model.ExecutionStatus;
import com.autorun.model.User;
import com.autorun.service.AuditService;
import com.autorun.service.ExecutionService;
import com.autorun.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.nio.charset.StandardCharsets;
import java.util.List;

@Controller
@RequestMapping("/executions")
public class ExecutionViewController extends BaseViewController {

    private final ExecutionService executionService;
    private final AuditService auditService;

    public ExecutionViewController(UserService userService,
                                   ExecutionService executionService,
                                   AuditService auditService) {
        super(userService);
        this.executionService = executionService;
        this.auditService = auditService;
    }

    @GetMapping
    public String list(@RequestParam(required = false) Long scriptId,
                       @RequestParam(required = false) ExecutionStatus status,
                       Authentication authentication,
                       Model model) {
        User user = currentUser(authentication);
        List<ExecutionLog> executions = executionService.list(scriptId, status, user);
        model.addAttribute("executions", executions);
        model.addAttribute("selectedScriptId", scriptId);
        model.addAttribute("selectedStatus", status);
        model.addAttribute("statuses", ExecutionStatus.values());
        return "executions";
    }

    @GetMapping("/{id}")
    public String detail(@PathVariable Long id, Model model) {
        ExecutionLog execution = executionService.get(id);
        model.addAttribute("execution", execution);
        return "execution-detail";
    }

    @GetMapping(value = "/{id}/log", produces = MediaType.TEXT_PLAIN_VALUE)
    public ResponseEntity<String> log(@PathVariable Long id, @RequestParam(required = false) Integer tail) {
        return ResponseEntity.ok()
                .contentType(new MediaType("text", "plain", StandardCharsets.UTF_8))
                .body(executionService.getLog(id, tail));
    }

    @GetMapping(value = "/{id}/download", produces = MediaType.TEXT_PLAIN_VALUE)
    public ResponseEntity<byte[]> download(@PathVariable Long id) {
        byte[] bytes = executionService.getLog(id, null).getBytes(StandardCharsets.UTF_8);
        return ResponseEntity.ok()
                .header("Content-Disposition", "attachment; filename=\"execution-%d.log\"".formatted(id))
                .contentType(new MediaType("text", "plain", StandardCharsets.UTF_8))
                .body(bytes);
    }

    @GetMapping(value = "/{id}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@PathVariable Long id) {
        return executionService.stream(id);
    }

    @PostMapping("/{id}/cancel")
    public String cancel(@PathVariable Long id, Authentication authentication,
                         RedirectAttributes redirect, HttpServletRequest http) {
        User user = currentUser(authentication);
        executionService.cancel(id);
        auditService.record(user, "EXECUTION_CANCELLED", "EXECUTION", id.toString(),
                "Requested cancellation of execution #" + id, http);
        redirect.addFlashAttribute("flashSuccess", "Cancellation requested");
        return "redirect:/executions/" + id;
    }
}
