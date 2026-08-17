package com.autorun.repository;

import com.autorun.model.ApprovalRequest;
import com.autorun.model.ApprovalStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ApprovalRequestRepository extends JpaRepository<ApprovalRequest, Long> {
    long countByStatus(ApprovalStatus status);
    List<ApprovalRequest> findByStatusOrderByRequestedAtDesc(ApprovalStatus status);
    List<ApprovalRequest> findTop20ByOrderByRequestedAtDesc();
    List<ApprovalRequest> findByRequestedByIdOrderByRequestedAtDesc(Long userId);
}
