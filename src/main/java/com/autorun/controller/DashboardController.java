package com.autorun.controller;

import com.autorun.model.ExecutionLog;
import com.autorun.model.ExecutionStatus;
import com.autorun.repository.ApprovalRequestRepository;
import com.autorun.repository.ExecutionLogRepository;
import com.autorun.repository.ScriptJobRepository;
import com.autorun.repository.ScriptRepository;
import com.autorun.repository.WorkflowRepository;
import com.autorun.service.ExecutionService;
import com.autorun.service.UserService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Controller
public class DashboardController extends BaseViewController {

    private final ScriptRepository scriptRepository;
    private final ScriptJobRepository jobRepository;
    private final ExecutionLogRepository executionLogRepository;
    private final ExecutionService executionService;
    private final WorkflowRepository workflowRepository;
    private final ApprovalRequestRepository approvalRequestRepository;

    public DashboardController(UserService userService,
                               ScriptRepository scriptRepository,
                               ScriptJobRepository jobRepository,
                               ExecutionLogRepository executionLogRepository,
                               ExecutionService executionService,
                               WorkflowRepository workflowRepository,
                               ApprovalRequestRepository approvalRequestRepository) {
        super(userService);
        this.scriptRepository = scriptRepository;
        this.jobRepository = jobRepository;
        this.executionLogRepository = executionLogRepository;
        this.executionService = executionService;
        this.workflowRepository = workflowRepository;
        this.approvalRequestRepository = approvalRequestRepository;
    }

    @GetMapping("/")
    public String index() {
        return "redirect:/dashboard";
    }

    @GetMapping("/dashboard")
    public String dashboard(Model model) {
        List<ExecutionLog> recent = executionLogRepository.findTop12ByOrderByStartedAtDesc();

        long totalExecutions = executionLogRepository.count();
        long failed = executionLogRepository.countByStatus(ExecutionStatus.FAILED)
                + executionLogRepository.countByStatus(ExecutionStatus.TIMEOUT);
        long succeeded = executionLogRepository.countByStatus(ExecutionStatus.SUCCESS);
        int successRate = totalExecutions == 0 ? 100 : (int) Math.round(succeeded * 100.0 / totalExecutions);

        Map<String, Long> byStatus = Map.of(
                "SUCCESS", succeeded,
                "FAILED", executionLogRepository.countByStatus(ExecutionStatus.FAILED),
                "TIMEOUT", executionLogRepository.countByStatus(ExecutionStatus.TIMEOUT),
                "CANCELLED", executionLogRepository.countByStatus(ExecutionStatus.CANCELLED),
                "RUNNING", executionLogRepository.countByStatus(ExecutionStatus.RUNNING));

        // Patch status data
        List<String> PATCH_SCRIPTS = List.of(
                "patch_apt", "win_patch", "linux_patch", "thirdparty_patch",
                "patch_verify", "patch_rollback", "patch_inventory", "patch_compliance",
                "patch_orchestrator", "daily_report");
        List<ExecutionLog> recentPatchRuns =
                executionLogRepository.findTop20ByScriptNameInOrderByStartedAtDesc(PATCH_SCRIPTS);
        List<Object[]> patchStatusRows =
                executionLogRepository.countByStatusForScriptsContaining("patch");
        Map<String, Map<String, Long>> patchByScript = new LinkedHashMap<>();
        for (Object[] row : patchStatusRows) {
            String scriptName = (String) row[0];
            String status = ((ExecutionStatus) row[1]).name();
            Long count = (Long) row[2];
            patchByScript.computeIfAbsent(scriptName, k -> new LinkedHashMap<>()).put(status, count);
        }

        model.addAttribute("scriptCount", scriptRepository.count());
        model.addAttribute("jobCount", jobRepository.count());
        model.addAttribute("executionCount", totalExecutions);
        model.addAttribute("runningCount", executionService.runningCount());
        model.addAttribute("failedCount", failed);
        model.addAttribute("successRate", successRate);
        model.addAttribute("workflowCount", workflowRepository.count());
        model.addAttribute("pendingApprovals", approvalRequestRepository.countByStatus(com.autorun.model.ApprovalStatus.PENDING));
        model.addAttribute("recentExecutions", recent);
        model.addAttribute("byStatus", byStatus);
        model.addAttribute("recentPatchRuns", recentPatchRuns);
        model.addAttribute("patchByScript", patchByScript);
        return "dashboard";
    }
}
