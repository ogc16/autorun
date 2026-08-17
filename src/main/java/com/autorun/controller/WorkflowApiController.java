package com.autorun.controller;

import com.autorun.model.User;
import com.autorun.model.Workflow;
import com.autorun.model.WorkflowExecution;
import com.autorun.model.WorkflowStep;
import com.autorun.service.WorkflowService;
import com.autorun.util.JsonUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/workflows")
public class WorkflowApiController {

    private static final ObjectMapper mapper = new ObjectMapper();
    private final WorkflowService workflowService;

    public WorkflowApiController(WorkflowService workflowService) {
        this.workflowService = workflowService;
    }

    @GetMapping
    public List<Workflow> list(@RequestParam(required = false) String search) {
        return workflowService.list(search);
    }

    @GetMapping("/{id}")
    public Workflow get(@PathVariable Long id) {
        return workflowService.get(id);
    }

    @GetMapping("/{id}/steps")
    public List<WorkflowStep> steps(@PathVariable Long id) {
        return workflowService.parseSteps(workflowService.get(id));
    }

    @PostMapping
    public Workflow create(@RequestBody Map<String, Object> body,
                           @AuthenticationPrincipal User user) throws Exception {
        String name = (String) body.get("name");
        String description = (String) body.get("description");
        String tags = (String) body.get("tags");
        boolean enabled = (boolean) body.getOrDefault("enabled", true);
        @SuppressWarnings("unchecked")
        List<WorkflowStep> steps = mapper.convertValue(body.get("steps"),
                new TypeReference<>() {});
        return workflowService.create(user, name, description, tags, steps, enabled);
    }

    @PutMapping("/{id}")
    public Workflow update(@PathVariable Long id, @RequestBody Map<String, Object> body) throws Exception {
        String name = (String) body.get("name");
        String description = (String) body.get("description");
        String tags = (String) body.get("tags");
        Boolean enabled = (Boolean) body.getOrDefault("enabled", true);
        List<WorkflowStep> steps = null;
        if (body.containsKey("steps")) {
            steps = mapper.convertValue(body.get("steps"), new TypeReference<>() {});
        }
        return workflowService.update(id, name, description, tags, steps, enabled != null ? enabled : true);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        workflowService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/run")
    public WorkflowExecution run(@PathVariable Long id, @AuthenticationPrincipal User user) {
        return workflowService.runWorkflow(id, user);
    }

    @PostMapping("/executions/{executionId}/cancel")
    public ResponseEntity<Void> cancel(@PathVariable Long executionId) {
        workflowService.cancel(executionId);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/executions")
    public List<WorkflowExecution> recentExecutions() {
        return workflowService.recentExecutions();
    }

    @GetMapping("/executions/{id}")
    public WorkflowExecution execution(@PathVariable Long id) {
        return workflowService.getExecution(id);
    }
}
