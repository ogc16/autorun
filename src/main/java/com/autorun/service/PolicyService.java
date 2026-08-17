package com.autorun.service;

import com.autorun.config.ConflictException;
import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.Policy;
import com.autorun.model.User;
import com.autorun.repository.PolicyRepository;
import org.springframework.scheduling.quartz.SchedulerFactoryBean;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class PolicyService {

    private final PolicyRepository policyRepository;
    private final SchedulerFactoryBean schedulerFactory;

    public PolicyService(PolicyRepository policyRepository,
                         SchedulerFactoryBean schedulerFactory) {
        this.policyRepository = policyRepository;
        this.schedulerFactory = schedulerFactory;
    }

    public List<Policy> list() {
        return policyRepository.findAll();
    }

    public Policy get(Long id) {
        return policyRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Policy not found: " + id));
    }

    public Policy create(User user, String name, String description, Long clientGroupId,
                         Long scriptId, String cronExpression, String timeZone,
                         String argumentsJson, String notifyOn, boolean enabled) {
        if (policyRepository.existsByName(name)) {
            throw new ConflictException("Policy name already exists: " + name);
        }
        Policy p = new Policy();
        p.setName(name);
        p.setDescription(description);
        p.setCronExpression(cronExpression);
        p.setTimeZone(timeZone != null ? timeZone : "UTC");
        p.setArgumentsJson(argumentsJson);
        p.setNotifyOn(notifyOn != null ? notifyOn : "FAILURE");
        p.setEnabled(enabled);
        p.setCreatedBy(user);
        return policyRepository.save(p);
    }

    public Policy update(Long id, String name, String description, Long clientGroupId,
                         Long scriptId, String cronExpression, String timeZone,
                         String argumentsJson, String notifyOn, boolean enabled) {
        Policy p = get(id);
        if (name != null) p.setName(name);
        if (description != null) p.setDescription(description);
        if (cronExpression != null) p.setCronExpression(cronExpression);
        if (timeZone != null) p.setTimeZone(timeZone);
        if (argumentsJson != null) p.setArgumentsJson(argumentsJson);
        if (notifyOn != null) p.setNotifyOn(notifyOn);
        p.setEnabled(enabled);
        return policyRepository.save(p);
    }

    public void delete(Long id) {
        policyRepository.delete(get(id));
    }

    public List<Policy> findByClientGroup(Long clientGroupId) {
        return policyRepository.findByClientGroupId(clientGroupId);
    }
}
