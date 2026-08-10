package com.autorun.repository;

import com.autorun.model.ExecutionLog;
import com.autorun.model.ExecutionStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ExecutionLogRepository extends JpaRepository<ExecutionLog, Long> {

    long countByStatus(ExecutionStatus status);

    List<ExecutionLog> findTop12ByOrderByStartedAtDesc();

    List<ExecutionLog> findByScriptIdOrderByStartedAtDesc(Long scriptId);

    List<ExecutionLog> findByUserIdOrderByStartedAtDesc(Long userId);

    Optional<ExecutionLog> findFirstByScriptIdOrderByStartedAtDesc(Long scriptId);
}
