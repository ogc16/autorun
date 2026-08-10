package com.autorun.repository;

import com.autorun.model.ScriptJob;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ScriptJobRepository extends JpaRepository<ScriptJob, Long> {

    Optional<ScriptJob> findByName(String name);

    boolean existsByName(String name);

    List<ScriptJob> findByScriptId(Long scriptId);
}
