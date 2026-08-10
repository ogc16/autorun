package com.autorun.controller;

import com.autorun.model.User;
import com.autorun.service.AuditService;
import com.autorun.service.UserService;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/audit")
public class AuditViewController extends BaseViewController {

    private final AuditService auditService;

    public AuditViewController(UserService userService, AuditService auditService) {
        super(userService);
        this.auditService = auditService;
    }

    @GetMapping
    public String list(Authentication authentication, Model model) {
        User user = currentUser(authentication);
        model.addAttribute("entries", auditService.all(user));
        return "audit";
    }
}
