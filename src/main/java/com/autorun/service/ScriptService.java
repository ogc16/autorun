package com.autorun.service;

import com.autorun.config.ConflictException;
import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.FileType;
import com.autorun.model.Script;
import com.autorun.model.ScriptParam;
import com.autorun.model.User;
import com.autorun.repository.ScriptJobRepository;
import com.autorun.repository.ScriptRepository;
import com.autorun.util.JsonUtil;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service
public class ScriptService {

    private final ScriptRepository scriptRepository;
    private final ScriptJobRepository scriptJobRepository;
    private final StorageService storageService;

    public ScriptService(ScriptRepository scriptRepository,
                         ScriptJobRepository scriptJobRepository,
                         StorageService storageService) {
        this.scriptRepository = scriptRepository;
        this.scriptJobRepository = scriptJobRepository;
        this.storageService = storageService;
    }

    @Transactional(readOnly = true)
    public List<Script> list(String search, String tag) {
        List<Script> all = scriptRepository.findAll();
        List<Script> result = new ArrayList<>(all);
        if (search != null && !search.isBlank()) {
            String q = search.toLowerCase();
            result.removeIf(s -> !(s.getName() != null && s.getName().toLowerCase().contains(q)
                    || s.getDescription() != null && s.getDescription().toLowerCase().contains(q)));
        }
        if (tag != null && !tag.isBlank()) {
            String t = tag.toLowerCase();
            result.removeIf(s -> !(s.getTags() != null && s.getTags().toLowerCase().contains(t)));
        }
        result.sort(Comparator.comparing(Script::getName));
        return result;
    }

    @Transactional(readOnly = true)
    public Script get(Long id) {
        return scriptRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Script not found: " + id));
    }

    @Transactional
    public Script create(User user, String name, String description, List<String> tags,
                         List<ScriptParam> params, MultipartFile file) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("Script name is required");
        }
        if (scriptRepository.existsByName(name.trim())) {
            throw new ConflictException("A script named '%s' already exists".formatted(name));
        }
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("A script file is required");
        }
        String original = file.getOriginalFilename() == null ? name : file.getOriginalFilename();
        FileType type = FileType.fromFilename(original);

        Script script = new Script();
        script.setName(name.trim());
        script.setFilename(original);
        script.setFileType(type);
        script.setDescription(description);
        script.setTags(tags == null || tags.isEmpty() ? null : String.join(",", tags));
        script.setParametersJson(JsonUtil.serializeParams(params));
        script.setSizeBytes(file.getSize());
        script.setCreatedBy(user);
        script.setCreatedAt(LocalDateTime.now());
        script.setUpdatedAt(LocalDateTime.now());
        try {
            storageService.writeScript(original, file.getBytes());
        } catch (IOException e) {
            throw new IllegalStateException("Failed to store uploaded script", e);
        }
        script.setStoragePath(storageService.scriptPath(original).toString());
        return scriptRepository.save(script);
    }

    @Transactional
    public Script update(Long id, String name, String description, List<String> tags,
                         List<ScriptParam> params, MultipartFile file) {
        Script script = get(id);
        if (name != null && !name.isBlank() && !script.getName().equals(name.trim())) {
            if (scriptRepository.existsByName(name.trim())) {
                throw new ConflictException("A script named '%s' already exists".formatted(name));
            }
            script.setName(name.trim());
        }
        if (description != null) {
            script.setDescription(description);
        }
        if (tags != null) {
            script.setTags(tags.isEmpty() ? null : String.join(",", tags));
        }
        if (params != null) {
            script.setParametersJson(JsonUtil.serializeParams(params));
        }
        if (file != null && !file.isEmpty()) {
            String original = file.getOriginalFilename();
            FileType type = FileType.fromFilename(original);
            if (type != script.getFileType()) {
                throw new IllegalArgumentException("Replacing file must be the same type (%s)".formatted(script.getFileType().extension()));
            }
            storageService.writeScript(script.getFilename(), getBytes(file));
            script.setSizeBytes(file.getSize());
        }
        script.setUpdatedAt(LocalDateTime.now());
        return scriptRepository.save(script);
    }

    @Transactional
    public void delete(Long id) {
        Script script = get(id);
        List<com.autorun.model.ScriptJob> jobs = scriptJobRepository.findByScriptId(id);
        if (!jobs.isEmpty()) {
            throw new ConflictException("Script is referenced by %d scheduled job(s); delete those first".formatted(jobs.size()));
        }
        storageService.deleteScript(script.getFilename());
        scriptRepository.delete(script);
    }

    public String readContent(Script script) {
        return storageService.readScriptContent(script.getFilename());
    }

    public byte[] readBytes(Script script) {
        return storageService.readScriptBytes(script.getFilename());
    }

    private byte[] getBytes(MultipartFile file) {
        try {
            return file.getBytes();
        } catch (IOException e) {
            throw new IllegalStateException("Failed to read upload", e);
        }
    }
}
