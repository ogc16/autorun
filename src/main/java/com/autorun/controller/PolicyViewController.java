package com.autorun.controller;

import com.autorun.model.ClientGroup;
import com.autorun.model.Policy;
import com.autorun.service.ClientGroupService;
import com.autorun.service.PolicyService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Controller
@RequestMapping("/policies")
public class PolicyViewController {

    private final PolicyService policyService;
    private final ClientGroupService clientGroupService;

    public PolicyViewController(PolicyService policyService, ClientGroupService clientGroupService) {
        this.policyService = policyService;
        this.clientGroupService = clientGroupService;
    }

    @GetMapping
    public String list(Model model) {
        model.addAttribute("policies", policyService.list());
        model.addAttribute("clientGroups", clientGroupService.list(null));
        return "policies";
    }

    @GetMapping("/client-groups")
    public String clientGroups(Model model) {
        model.addAttribute("clientGroups", clientGroupService.list(null));
        return "client-groups";
    }

    @GetMapping("/{id}")
    public String detail(@PathVariable Long id, Model model) {
        model.addAttribute("policy", policyService.get(id));
        model.addAttribute("clientGroups", clientGroupService.list(null));
        return "policy-detail";
    }
}
