package com.autorun.controller;

import com.autorun.model.User;
import com.autorun.service.WorkflowService;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

@Controller
@RequestMapping("/workflows")
public class WorkflowViewController {

    private final WorkflowService workflowService;

    public WorkflowViewController(WorkflowService workflowService) {
        this.workflowService = workflowService;
    }

    @GetMapping
    public String list(@RequestParam(required = false) String search, Model model) {
        model.addAttribute("workflows", workflowService.list(search));
        model.addAttribute("search", search);
        return "workflows";
    }

    @GetMapping("/{id}")
    public String detail(@PathVariable Long id, Model model) {
        model.addAttribute("workflow", workflowService.get(id));
        model.addAttribute("steps", workflowService.parseSteps(workflowService.get(id)));
        model.addAttribute("executions", workflowService.recentExecutions());
        return "workflow-detail";
    }
}
