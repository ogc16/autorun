package com.autorun.controller;

import com.autorun.model.ApprovalRequest;
import com.autorun.service.ApprovalService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

@Controller
@RequestMapping("/approvals")
public class ApprovalViewController {

    private final ApprovalService approvalService;

    public ApprovalViewController(ApprovalService approvalService) {
        this.approvalService = approvalService;
    }

    @GetMapping
    public String list(Model model) {
        model.addAttribute("pending", approvalService.listPending());
        model.addAttribute("recent", approvalService.recent());
        model.addAttribute("pendingCount", approvalService.pendingCount());
        return "approvals";
    }

    @GetMapping("/{id}")
    public String detail(@PathVariable Long id, Model model) {
        model.addAttribute("approval", approvalService.get(id));
        return "approval-detail";
    }
}
