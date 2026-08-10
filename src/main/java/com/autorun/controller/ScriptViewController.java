package com.autorun.controller;

import com.autorun.model.ExecutionLog;
import com.autorun.model.Script;
import com.autorun.model.ScriptParam;
import com.autorun.model.TriggerType;
import com.autorun.model.User;
import com.autorun.repository.ExecutionLogRepository;
import com.autorun.service.AuditService;
import com.autorun.service.ExecutionService;
import com.autorun.service.ScriptService;
import com.autorun.service.UserService;
import com.autorun.util.JsonUtil;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Controller
@RequestMapping("/scripts")
public class ScriptViewController extends BaseViewController {

    private final ScriptService scriptService;
    private final ExecutionService executionService;
    private final ExecutionLogRepository executionLogRepository;
    private final AuditService auditService;

    public ScriptViewController(UserService userService,
                                ScriptService scriptService,
                                ExecutionService executionService,
                                ExecutionLogRepository executionLogRepository,
                                AuditService auditService) {
        super(userService);
        this.scriptService = scriptService;
        this.executionService = executionService;
        this.executionLogRepository = executionLogRepository;
        this.auditService = auditService;
    }

    @GetMapping
    public String list(@RequestParam(required = false) String search,
                       @RequestParam(required = false) String tag,
                       Model model) {
        model.addAttribute("scripts", scriptService.list(search, tag));
        model.addAttribute("search", search);
        model.addAttribute("tag", tag);
        return "scripts";
    }

    @GetMapping("/new")
    public String newForm(Model model) {
        model.addAttribute("script", new Script());
        model.addAttribute("mode", "create");
        return "script-form";
    }

    @GetMapping("/{id}/edit")
    public String editForm(@PathVariable Long id, Model model) {
        model.addAttribute("script", scriptService.get(id));
        model.addAttribute("mode", "edit");
        return "script-form";
    }

    @PostMapping("/new")
    public String create(@RequestParam("name") String name,
                         @RequestParam(required = false) String description,
                         @RequestParam(required = false) String tags,
                         @RequestParam(required = false) String parametersJson,
                         @RequestParam("file") MultipartFile file,
                         Authentication authentication,
                         RedirectAttributes redirect,
                         HttpServletRequest http) {
        User user = currentUser(authentication);
        try {
            Script script = scriptService.create(user, name, description,
                    splitTags(tags), JsonUtil.parseParams(parametersJson), file);
            auditService.record(user, "SCRIPT_CREATED", "SCRIPT", script.getId().toString(),
                    "Uploaded script '" + script.getName() + "'", http);
            redirect.addFlashAttribute("flashSuccess", "Script uploaded successfully");
            return "redirect:/scripts/" + script.getId();
        } catch (Exception e) {
            redirect.addFlashAttribute("flashError", e.getMessage());
            return "redirect:/scripts/new";
        }
    }

    @GetMapping("/{id}")
    public String detail(@PathVariable Long id, Model model) {
        Script script = scriptService.get(id);
        List<ScriptParam> params = JsonUtil.parseParams(script.getParametersJson());
        List<ExecutionLog> recent = executionLogRepository.findByScriptIdOrderByStartedAtDesc(id)
                .stream().limit(10).toList();
        model.addAttribute("script", script);
        model.addAttribute("params", params);
        model.addAttribute("recentExecutions", recent);
        model.addAttribute("content", scriptService.readContent(script));
        return "script-detail";
    }

    @PostMapping("/{id}/run")
    public String run(@PathVariable Long id,
                      @RequestParam Map<String, String> allParams,
                      @RequestParam(required = false) String rawArgs,
                      @RequestParam(defaultValue = "FAILURE") String notifyOn,
                      Authentication authentication,
                      RedirectAttributes redirect,
                      HttpServletRequest http) {
        User user = currentUser(authentication);
        Script script = scriptService.get(id);
        try {
            Map<String, String> args = extractArguments(script, allParams);
            ExecutionLog exec = executionService.execute(script, args, Map.of(), null, notifyOn,
                    TriggerType.MANUAL, user, null);
            auditService.record(user, "SCRIPT_RUN", "SCRIPT", id.toString(),
                    "Manual execution #%d started for script '%s'".formatted(exec.getId(), script.getName()), http);
            return "redirect:/executions/" + exec.getId();
        } catch (Exception e) {
            redirect.addFlashAttribute("flashError", e.getMessage());
            return "redirect:/scripts/" + id;
        }
    }

    @PostMapping("/{id}/edit")
    public String edit(@PathVariable Long id,
                       @RequestParam(required = false) String name,
                       @RequestParam(required = false) String description,
                       @RequestParam(required = false) String tags,
                       @RequestParam(required = false) String parametersJson,
                       @RequestParam(required = false) MultipartFile file,
                       Authentication authentication,
                       RedirectAttributes redirect,
                       HttpServletRequest http) {
        User user = currentUser(authentication);
        try {
            Script script = scriptService.update(id, name, description,
                    splitTags(tags), JsonUtil.parseParams(parametersJson), file);
            auditService.record(user, "SCRIPT_UPDATED", "SCRIPT", id.toString(),
                    "Updated script '" + script.getName() + "'", http);
            redirect.addFlashAttribute("flashSuccess", "Script updated");
            return "redirect:/scripts/" + id;
        } catch (Exception e) {
            redirect.addFlashAttribute("flashError", e.getMessage());
            return "redirect:/scripts/" + id;
        }
    }

    @PostMapping("/{id}/delete")
    public String delete(@PathVariable Long id,
                         Authentication authentication,
                         RedirectAttributes redirect,
                         HttpServletRequest http) {
        User user = currentUser(authentication);
        if (!"ADMIN".equals(user.getRole().name())) {
            redirect.addFlashAttribute("flashError", "Only admins can delete scripts");
            return "redirect:/scripts/" + id;
        }
        Script script = scriptService.get(id);
        try {
            scriptService.delete(id);
            auditService.record(user, "SCRIPT_DELETED", "SCRIPT", id.toString(),
                    "Deleted script '" + script.getName() + "'", http);
            redirect.addFlashAttribute("flashSuccess", "Script deleted");
            return "redirect:/scripts";
        } catch (Exception e) {
            redirect.addFlashAttribute("flashError", e.getMessage());
            return "redirect:/scripts/" + id;
        }
    }

    private Map<String, String> extractArguments(Script script, Map<String, String> allParams) {
        Map<String, String> args = new HashMap<>();
        for (ScriptParam p : JsonUtil.parseParams(script.getParametersJson())) {
            String v = allParams.get(p.getName());
            if (v != null && !v.isBlank()) {
                args.put(p.getName(), v);
            }
        }
        return args;
    }

    private List<String> splitTags(String tags) {
        if (tags == null || tags.isBlank()) {
            return null;
        }
        List<String> result = new ArrayList<>();
        for (String t : tags.split(",")) {
            if (!t.isBlank()) {
                result.add(t.trim());
            }
        }
        return result;
    }
}
