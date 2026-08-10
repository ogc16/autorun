package com.autorun.controller;

import com.autorun.model.ExecutionLog;
import com.autorun.model.ExecutionStatus;
import com.autorun.model.Script;
import com.autorun.model.TriggerType;
import com.autorun.model.User;
import com.autorun.security.AppUserDetails;
import com.autorun.service.AuditService;
import com.autorun.service.ExecutionService;
import com.autorun.service.ScriptService;
import com.autorun.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class ExecutionApiController {

    private final ExecutionService executionService;
    private final ScriptService scriptService;
    private final UserService userService;
    private final AuditService auditService;

    public ExecutionApiController(ExecutionService executionService,
                                  ScriptService scriptService,
                                  UserService userService,
                                  AuditService auditService) {
        this.executionService = executionService;
        this.scriptService = scriptService;
        this.userService = userService;
        this.auditService = auditService;
    }

    @PostMapping("/scripts/{id}/execute")
    public ResponseEntity<ExecutionLog> execute(@PathVariable Long id,
                                                @RequestBody(required = false) ExecuteRequest request,
                                                Authentication authentication,
                                                HttpServletRequest http) {
        User user = currentUser(authentication);
        Script script = scriptService.get(id);
        ExecuteRequest req = request == null ? new ExecuteRequest(Map.of(), Map.of(), null, "FAILURE") : request;
        ExecutionLog exec = executionService.execute(script, req.arguments(), req.env(),
                req.timeoutSeconds(), req.notifyOn(), TriggerType.MANUAL, user, null);
        auditService.record(user, "SCRIPT_RUN", "SCRIPT", id.toString(),
                "Manual execution #%d started for script '%s'".formatted(exec.getId(), script.getName()), http);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(exec);
    }

    @GetMapping("/executions")
    public List<ExecutionLog> list(@RequestParam(required = false) Long scriptId,
                                   @RequestParam(required = false) ExecutionStatus status,
                                   Authentication authentication) {
        return executionService.list(scriptId, status, currentUser(authentication));
    }

    @GetMapping("/executions/{id}")
    public ExecutionLog get(@PathVariable Long id) {
        return executionService.get(id);
    }

    @GetMapping(value = "/executions/{id}/log", produces = MediaType.TEXT_PLAIN_VALUE)
    public ResponseEntity<String> log(@PathVariable Long id,
                                      @RequestParam(required = false) Integer tail,
                                      @RequestParam(defaultValue = "false") boolean download) {
        String content = executionService.getLog(id, tail);
        return ResponseEntity.ok()
                .contentType(new MediaType("text", "plain", StandardCharsets.UTF_8))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        download ? "attachment; filename=\"execution-%d.log\"".formatted(id) : "inline")
                .body(content);
    }

    @GetMapping(value = "/executions/{id}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@PathVariable Long id) {
        return executionService.stream(id);
    }

    @PostMapping("/executions/{id}/cancel")
    public ResponseEntity<ExecutionLog> cancel(@PathVariable Long id,
                                               Authentication authentication,
                                               HttpServletRequest http) {
        User user = currentUser(authentication);
        executionService.cancel(id);
        auditService.record(user, "EXECUTION_CANCELLED", "EXECUTION", id.toString(),
                "Requested cancellation of execution #" + id, http);
        return ResponseEntity.accepted().body(executionService.get(id));
    }

    private User currentUser(Authentication authentication) {
        AppUserDetails principal = (AppUserDetails) authentication.getPrincipal();
        return userService.get(principal.getId());
    }

    public record ExecuteRequest(Map<String, String> arguments,
                                 Map<String, String> env,
                                 Integer timeoutSeconds,
                                 String notifyOn) {
    }
}
