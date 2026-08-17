package com.autorun.controller;

import com.autorun.model.Policy;
import com.autorun.model.ClientGroup;
import com.autorun.service.PolicyService;
import com.autorun.service.ClientGroupService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/policies")
public class PolicyApiController {

    private final PolicyService policyService;
    private final ClientGroupService clientGroupService;

    public PolicyApiController(PolicyService policyService, ClientGroupService clientGroupService) {
        this.policyService = policyService;
        this.clientGroupService = clientGroupService;
    }

    @GetMapping
    public List<Policy> list() {
        return policyService.list();
    }

    @GetMapping("/{id}")
    public Policy get(@PathVariable Long id) {
        return policyService.get(id);
    }

    @PostMapping
    public Policy create(@RequestBody java.util.Map<String, Object> body,
                         @org.springframework.security.core.annotation.AuthenticationPrincipal com.autorun.model.User user) {
        String name = (String) body.get("name");
        String description = (String) body.get("description");
        Long clientGroupId = body.get("clientGroupId") != null ? ((Number) body.get("clientGroupId")).longValue() : null;
        Long scriptId = ((Number) body.get("scriptId")).longValue();
        String cronExpression = (String) body.get("cronExpression");
        String timeZone = (String) body.getOrDefault("timeZone", "UTC");
        String argumentsJson = (String) body.get("argumentsJson");
        String notifyOn = (String) body.getOrDefault("notifyOn", "FAILURE");
        Boolean enabled = (Boolean) body.getOrDefault("enabled", true);

        Policy p = policyService.create(user, name, description, clientGroupId, scriptId,
                cronExpression, timeZone, argumentsJson, notifyOn, enabled != null ? enabled : true);

        if (clientGroupId != null) {
            p.setClientGroup(clientGroupService.get(clientGroupId));
        }
        return policyService.update(p.getId(), null, null, clientGroupId, scriptId,
                null, null, null, null, enabled != null ? enabled : true);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        policyService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
