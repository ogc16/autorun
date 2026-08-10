package com.autorun.controller;

import com.autorun.model.NotificationSettings;
import com.autorun.service.NotificationService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

@Controller
@RequestMapping("/settings")
public class SettingsViewController {

    private final NotificationService notificationService;

    public SettingsViewController(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    @GetMapping
    public String form(Model model) {
        model.addAttribute("settings", notificationService.getSettings());
        return "settings";
    }

    @PostMapping
    public String save(@ModelAttribute NotificationSettings settings, RedirectAttributes redirect) {
        notificationService.saveSettings(settings);
        redirect.addFlashAttribute("flashSuccess", "Notification settings saved");
        return "redirect:/settings";
    }
}
