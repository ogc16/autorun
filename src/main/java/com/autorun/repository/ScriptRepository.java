package com.autorun.repository;

import com.autorun.model.Script;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ScriptRepository extends JpaRepository<Script, Long> {

    Optional<Script> findByName(String name);

    boolean existsByName(String name);

    List<Script> findByNameContainingIgnoreCaseOrDescriptionContainingIgnoreCase(String name, String description);
}
