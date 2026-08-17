package com.autorun.repository;

import com.autorun.model.ExecutionLog;
import com.autorun.model.ExecutionStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface ExecutionLogRepository extends JpaRepository<ExecutionLog, Long> {

    long countByStatus(ExecutionStatus status);

    List<ExecutionLog> findTop12ByOrderByStartedAtDesc();

    List<ExecutionLog> findByScriptIdOrderByStartedAtDesc(Long scriptId);

    List<ExecutionLog> findByUserIdOrderByStartedAtDesc(Long userId);

    Optional<ExecutionLog> findFirstByScriptIdOrderByStartedAtDesc(Long scriptId);

    @Query("SELECT e.script.name as scriptName, e.status as status, COUNT(e) as cnt " +
           "FROM ExecutionLog e WHERE e.script.name LIKE %:keyword% GROUP BY e.script.name, e.status")
    List<Object[]> countByStatusForScriptsContaining(@Param("keyword") String keyword);

    @Query("SELECT e FROM ExecutionLog e WHERE e.script.name LIKE %:keyword% ORDER BY e.startedAt DESC")
    List<ExecutionLog> findTop10ByScriptNameContainingOrderByStartedAtDesc(@Param("keyword") String keyword);

    @Query("SELECT e FROM ExecutionLog e WHERE e.script.name IN :names ORDER BY e.startedAt DESC")
    List<ExecutionLog> findTop20ByScriptNameInOrderByStartedAtDesc(@Param("names") List<String> names);
}
