package com.autorun.service;

import com.autorun.model.AuditLog;
import com.autorun.model.User;
import com.autorun.repository.AuditLogRepository;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class AuditService {

    private final AuditLogRepository auditLogRepository;

    public AuditService(AuditLogRepository auditLogRepository) {
        this.auditLogRepository = auditLogRepository;
    }

    @Transactional
    public AuditLog record(User user, String action, String targetType, String targetId,
                           String details, HttpServletRequest request) {
        AuditLog entry = new AuditLog();
        entry.setUser(user);
        entry.setAction(action);
        entry.setTargetType(targetType);
        entry.setTargetId(targetId);
        entry.setDetails(details);
        entry.setIpAddress(resolveIp(request));
        entry.setTimestamp(LocalDateTime.now());
        return auditLogRepository.save(entry);
    }

    public String resolveIp(HttpServletRequest request) {
        if (request == null) {
            return "system";
        }
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    @Transactional(readOnly = true)
    public List<AuditLog> recent(int limit, User user) {
        if (user != null && !"ADMIN".equals(user.getRole().name())) {
            return auditLogRepository.findByUserIdOrderByTimestampDesc(user.getId());
        }
        return auditLogRepository.findTop200ByOrderByTimestampDesc();
    }

    @Transactional(readOnly = true)
    public List<AuditLog> all(User user) {
        if (user != null && !"ADMIN".equals(user.getRole().name())) {
            return auditLogRepository.findByUserIdOrderByTimestampDesc(user.getId());
        }
        return auditLogRepository.findAll().stream()
                .sorted((a, b) -> b.getTimestamp().compareTo(a.getTimestamp()))
                .toList();
    }
}
