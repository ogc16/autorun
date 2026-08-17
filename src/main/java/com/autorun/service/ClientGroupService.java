package com.autorun.service;

import com.autorun.config.ConflictException;
import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.ClientGroup;
import com.autorun.repository.ClientGroupRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ClientGroupService {

    private final ClientGroupRepository clientGroupRepository;

    public ClientGroupService(ClientGroupRepository clientGroupRepository) {
        this.clientGroupRepository = clientGroupRepository;
    }

    public List<ClientGroup> list(String search) {
        if (search != null && !search.isBlank()) {
            return clientGroupRepository.findByNameContainingIgnoreCaseOrDescriptionContainingIgnoreCase(search, search);
        }
        return clientGroupRepository.findAll();
    }

    public ClientGroup get(Long id) {
        return clientGroupRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Client group not found: " + id));
    }

    public ClientGroup create(String name, String description, String tags) {
        if (clientGroupRepository.existsByName(name)) {
            throw new ConflictException("Client group name already exists: " + name);
        }
        ClientGroup cg = new ClientGroup();
        cg.setName(name);
        cg.setDescription(description);
        cg.setTags(tags);
        return clientGroupRepository.save(cg);
    }

    public ClientGroup update(Long id, String name, String description, String tags, boolean enabled) {
        ClientGroup cg = get(id);
        if (name != null) cg.setName(name);
        if (description != null) cg.setDescription(description);
        if (tags != null) cg.setTags(tags);
        cg.setEnabled(enabled);
        return clientGroupRepository.save(cg);
    }

    public void delete(Long id) {
        clientGroupRepository.delete(get(id));
    }
}
