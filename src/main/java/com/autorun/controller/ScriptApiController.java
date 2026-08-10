package com.autorun.controller;

import com.autorun.model.Script;
import com.autorun.model.User;
import com.autorun.security.AppUserDetails;
import com.autorun.service.AuditService;
import com.autorun.service.ScriptService;
import com.autorun.service.UserService;
import com.autorun.util.JsonUtil;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/scripts")
public class ScriptApiController {

    private final ScriptService scriptService;
    private final AuditService auditService;
    private final UserService userService;

    public ScriptApiController(ScriptService scriptService, AuditService auditService, UserService userService) {
        this.scriptService = scriptService;
        this.auditService = auditService;
        this.userService = userService;
    }

    @GetMapping
    public List<Script> list(@RequestParam(required = false) String search,
                             @RequestParam(required = false) String tag) {
        return scriptService.list(search, tag);
    }

    @GetMapping("/{id}")
    public Script get(@PathVariable Long id) {
        return scriptService.get(id);
    }

    @GetMapping("/{id}/content")
    public ResponseEntity<byte[]> content(@PathVariable Long id) {
        Script script = scriptService.get(id);
        return ResponseEntity.ok()
                .contentType(MediaType.TEXT_PLAIN)
                .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + script.getFilename() + "\"")
                .body(scriptService.readBytes(script));
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Script create(@RequestParam("name") String name,
                         @RequestParam(required = false) String description,
                         @RequestParam(required = false) String tags,
                         @RequestParam(required = false) String parameters,
                         @RequestPart("file") MultipartFile file,
                         Authentication authentication,
                         HttpServletRequest http) {
        User user = currentUser(authentication);
        Script script = scriptService.create(user, name, description, splitTags(tags),
                JsonUtil.parseParams(parameters), file);
        auditService.record(user, "SCRIPT_CREATED", "SCRIPT", script.getId().toString(),
                "Uploaded script '" + script.getName() + "'", http);
        return script;
    }

    @PutMapping(value = "/{id}", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Script update(@PathVariable Long id,
                         @RequestParam(required = false) String name,
                         @RequestParam(required = false) String description,
                         @RequestParam(required = false) String tags,
                         @RequestParam(required = false) String parameters,
                         @RequestPart(required = false) MultipartFile file,
                         Authentication authentication,
                         HttpServletRequest http) {
        User user = currentUser(authentication);
        Script script = scriptService.update(id, name, description, splitTags(tags),
                JsonUtil.parseParams(parameters), file);
        auditService.record(user, "SCRIPT_UPDATED", "SCRIPT", script.getId().toString(),
                "Updated script '" + script.getName() + "'", http);
        return script;
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id, Authentication authentication, HttpServletRequest http) {
        User user = currentUser(authentication);
        Script script = scriptService.get(id);
        scriptService.delete(id);
        auditService.record(user, "SCRIPT_DELETED", "SCRIPT", id.toString(),
                "Deleted script '" + script.getName() + "'", http);
    }

    private List<String> splitTags(String tags) {
        if (tags == null || tags.isBlank()) {
            return null;
        }
        return List.of(tags.split(",")).stream().map(String::trim).filter(s -> !s.isBlank()).toList();
    }

    private User currentUser(Authentication authentication) {
        AppUserDetails principal = (AppUserDetails) authentication.getPrincipal();
        return userService.get(principal.getId());
    }
}
