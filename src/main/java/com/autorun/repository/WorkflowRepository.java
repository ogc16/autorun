package com.autorun.repository;

import com.autorun.model.Workflow;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface WorkflowRepository extends JpaRepository<Workflow, Long> {
    boolean existsByName(String name);
    List<Workflow> findByEnabledTrue();
    List<Workflow> findByNameContainingIgnoreCaseOrDescriptionContainingIgnoreCase(String name, String description);
}
