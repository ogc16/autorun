package com.autorun.controller;

import com.autorun.model.AuditLog;
import com.autorun.model.User;
import com.autorun.security.AppUserDetails;
import com.autorun.service.AuditService;
import com.autorun.service.UserService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.util.List;

@RestController
@RequestMapping("/api/audit")
public class AuditApiController {

    private final AuditService auditService;
    private final UserService userService;

    public AuditApiController(AuditService auditService, UserService userService) {
        this.auditService = auditService;
        this.userService = userService;
    }

    @GetMapping
    public List<AuditLog> list(Authentication authentication) {
        return auditService.all(currentUser(authentication));
    }

    @GetMapping(value = "/export", produces = "text/csv")
    public void export(Authentication authentication, HttpServletResponse response) throws IOException {
        List<AuditLog> logs = auditService.all(currentUser(authentication));
        response.setContentType("text/csv");
        response.setHeader("Content-Disposition", "attachment; filename=\"audit-logs.csv\"");
        StringBuilder csv = new StringBuilder("id,timestamp,user,action,targetType,targetId,ipAddress,details\n");
        for (AuditLog log : logs) {
            csv.append(log.getId()).append(',')
                    .append(log.getTimestamp()).append(',')
                    .append(escapedCsv(log.getUser() == null ? "" : log.getUser().getUsername())).append(',')
                    .append(escapedCsv(log.getAction())).append(',')
                    .append(escapedCsv(log.getTargetType())).append(',')
                    .append(escapedCsv(log.getTargetId())).append(',')
                    .append(escapedCsv(log.getIpAddress())).append(',')
                    .append(escapedCsv(log.getDetails()))
                    .append('\n');
        }
        response.getWriter().write(csv.toString());
    }

    private String escapedCsv(String value) {
        if (value == null) {
            return "";
        }
        return "\"" + value.replace("\"", "\"\"") + "\"";
    }

    private User currentUser(Authentication authentication) {
        AppUserDetails principal = (AppUserDetails) authentication.getPrincipal();
        return userService.get(principal.getId());
    }
}
