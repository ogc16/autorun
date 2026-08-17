package com.autorun.controller;

import com.autorun.model.ApprovalRequest;
import com.autorun.model.Script;
import com.autorun.model.User;
import com.autorun.service.ApprovalService;
import com.autorun.service.ScriptService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/approvals")
public class ApprovalApiController {

    private final ApprovalService approvalService;
    private final ScriptService scriptService;

    public ApprovalApiController(ApprovalService approvalService, ScriptService scriptService) {
        this.approvalService = approvalService;
        this.scriptService = scriptService;
    }

    @GetMapping
    public List<ApprovalRequest> list() {
        return approvalService.recent();
    }

    @GetMapping("/pending")
    public List<ApprovalRequest> pending() {
        return approvalService.listPending();
    }

    @GetMapping("/{id}")
    public ApprovalRequest get(@PathVariable Long id) {
        return approvalService.get(id);
    }

    @PostMapping
    public ApprovalRequest create(@RequestBody Map<String, Object> body,
                                  @AuthenticationPrincipal User user) {
        Long scriptId = ((Number) body.get("scriptId")).longValue();
        String args = (String) body.getOrDefault("argumentsJson", "{}");
        Script script = scriptService.get(scriptId);
        return approvalService.create(script, args, user);
    }

    @PostMapping("/{id}/approve")
    public ApprovalRequest approve(@PathVariable Long id,
                                   @RequestBody Map<String, String> body,
                                   @AuthenticationPrincipal User user) {
        String note = body.getOrDefault("note", "Approved");
        return approvalService.approve(id, user, note);
    }

    @PostMapping("/{id}/reject")
    public ApprovalRequest reject(@PathVariable Long id,
                                  @RequestBody Map<String, String> body,
                                  @AuthenticationPrincipal User user) {
        String note = body.getOrDefault("note", "Rejected");
        return approvalService.reject(id, user, note);
    }
}
