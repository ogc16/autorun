package com.autorun.service;

import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.*;
import com.autorun.repository.ApprovalRequestRepository;
import com.autorun.util.JsonUtil;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class ApprovalService {

    private final ApprovalRequestRepository approvalRepository;
    private final ExecutionService executionService;

    public ApprovalService(ApprovalRequestRepository approvalRepository,
                           ExecutionService executionService) {
        this.approvalRepository = approvalRepository;
        this.executionService = executionService;
    }

    public ApprovalRequest create(Script script, String argumentsJson, User requestedBy) {
        ApprovalRequest req = new ApprovalRequest();
        req.setScript(script);
        req.setArgumentsJson(argumentsJson);
        req.setRequestedBy(requestedBy);
        req.setStatus(ApprovalStatus.PENDING);
        return approvalRepository.save(req);
    }

    public ApprovalRequest approve(Long id, User approver, String note) {
        ApprovalRequest req = get(id);
        if (req.getStatus() != ApprovalStatus.PENDING) {
            throw new IllegalStateException("Request is not pending");
        }
        req.setApprover(approver);
        req.setStatus(ApprovalStatus.APPROVED);
        req.setDecisionNote(note);
        req.setDecidedAt(LocalDateTime.now());
        req = approvalRepository.save(req);

        // Auto-execute the approved script
        ExecutionLog el = executionService.execute(
                req.getScript(),
                req.getArgumentsJson() != null ? JsonUtil.parseArguments(req.getArgumentsJson()) : Map.of(),
                null, 600, "ALWAYS",
                TriggerType.MANUAL, approver, null);
        req.setExecutionLog(el);
        approvalRepository.save(req);

        return req;
    }

    public ApprovalRequest reject(Long id, User approver, String note) {
        ApprovalRequest req = get(id);
        if (req.getStatus() != ApprovalStatus.PENDING) {
            throw new IllegalStateException("Request is not pending");
        }
        req.setApprover(approver);
        req.setStatus(ApprovalStatus.REJECTED);
        req.setDecisionNote(note);
        req.setDecidedAt(LocalDateTime.now());
        return approvalRepository.save(req);
    }

    public ApprovalRequest get(Long id) {
        return approvalRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Approval request not found: " + id));
    }

    public List<ApprovalRequest> listPending() {
        return approvalRepository.findByStatusOrderByRequestedAtDesc(ApprovalStatus.PENDING);
    }

    public List<ApprovalRequest> recent() {
        return approvalRepository.findTop20ByOrderByRequestedAtDesc();
    }

    public long pendingCount() {
        return approvalRepository.countByStatus(ApprovalStatus.PENDING);
    }
}
