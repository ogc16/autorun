package com.autorun.controller;

import com.autorun.model.NotificationSettings;
import com.autorun.service.NotificationService;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/notifications")
public class NotificationApiController {

    private final NotificationService notificationService;

    public NotificationApiController(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    @GetMapping("/settings")
    @PreAuthorize("hasRole('ADMIN')")
    public NotificationSettings get() {
        return notificationService.getSettings();
    }

    @PutMapping("/settings")
    @PreAuthorize("hasRole('ADMIN')")
    public NotificationSettings put(@RequestBody NotificationSettings settings) {
        return notificationService.saveSettings(settings);
    }

    @PostMapping("/test")
    @PreAuthorize("hasRole('ADMIN')")
    public Map<String, String> test(@RequestParam(defaultValue = "all") String channel) {
        return notificationService.sendTest(channel);
    }
}
