package com.autorun.repository;

import com.autorun.model.ClientGroup;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ClientGroupRepository extends JpaRepository<ClientGroup, Long> {
    boolean existsByName(String name);
    List<ClientGroup> findByNameContainingIgnoreCaseOrDescriptionContainingIgnoreCase(String name, String description);
}
