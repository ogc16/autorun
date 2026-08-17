package com.autorun.repository;

import com.autorun.model.ExecutionStatus;
import com.autorun.model.WorkflowExecution;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface WorkflowExecutionRepository extends JpaRepository<WorkflowExecution, Long> {
    List<WorkflowExecution> findTop20ByOrderByStartedAtDesc();
    List<WorkflowExecution> findByWorkflowIdOrderByStartedAtDesc(Long workflowId);
    long countByStatus(ExecutionStatus status);
    long countByWorkflowIdAndStatus(Long workflowId, ExecutionStatus status);
}
