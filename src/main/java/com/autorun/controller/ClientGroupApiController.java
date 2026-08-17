package com.autorun.controller;

import com.autorun.model.ClientGroup;
import com.autorun.service.ClientGroupService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/client-groups")
public class ClientGroupApiController {

    private final ClientGroupService clientGroupService;

    public ClientGroupApiController(ClientGroupService clientGroupService) {
        this.clientGroupService = clientGroupService;
    }

    @GetMapping
    public List<ClientGroup> list(@RequestParam(required = false) String search) {
        return clientGroupService.list(search);
    }

    @GetMapping("/{id}")
    public ClientGroup get(@PathVariable Long id) {
        return clientGroupService.get(id);
    }

    @PostMapping
    public ClientGroup create(@RequestBody java.util.Map<String, Object> body) {
        String name = (String) body.get("name");
        String description = (String) body.get("description");
        String tags = (String) body.get("tags");
        return clientGroupService.create(name, description, tags);
    }

    @PutMapping("/{id}")
    public ClientGroup update(@PathVariable Long id, @RequestBody java.util.Map<String, Object> body) {
        String name = (String) body.get("name");
        String description = (String) body.get("description");
        String tags = (String) body.get("tags");
        Boolean enabled = (Boolean) body.getOrDefault("enabled", true);
        return clientGroupService.update(id, name, description, tags, enabled != null ? enabled : true);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        clientGroupService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
