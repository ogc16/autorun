package com.autorun.repository;

import com.autorun.model.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {

    List<AuditLog> findTop200ByOrderByTimestampDesc();

    List<AuditLog> findByUserIdOrderByTimestampDesc(Long userId);
}
