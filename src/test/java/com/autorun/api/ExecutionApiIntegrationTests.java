package com.autorun.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class ExecutionApiIntegrationTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    private String loginAdmin() throws Exception {
        String body = objectMapper.writeValueAsString(new LoginRequest("admin", "admin123"));
        MvcResult result = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString())
                .path("accessToken").asText();
    }

    private String scriptContent() {
        if (System.getProperty("os.name").toLowerCase().contains("win")) {
            return "@echo off\r\nhello-autorun-test\r\nexit /b 0";
        }
        return "#!/bin/sh\necho hello-autorun-test\nexit 0\n";
    }

    private String scriptFilename() {
        return System.getProperty("os.name").toLowerCase().contains("win")
                ? "it-smoke-test.cmd"
                : "it-smoke-test.sh";
    }

    private long uploadScript(String token) throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file", scriptFilename(), "text/plain",
                scriptContent().getBytes(StandardCharsets.UTF_8));

        MvcResult result = mockMvc.perform(multipart("/api/scripts")
                        .file(file)
                        .param("name", "it-smoke-" + System.nanoTime())
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andReturn();

        return objectMapper.readTree(result.getResponse().getContentAsString())
                .path("id").asLong();
    }

    private String sleepContent() {
        if (System.getProperty("os.name").toLowerCase().contains("win")) {
            return "@echo off\r\nping -n 120 127.0.0.1 > nul\r\nexit /b 1";
        }
        return "#!/bin/sh\nexec sleep 120\nexit 0\n";
    }

    private String sleepFilename() {
        return System.getProperty("os.name").toLowerCase().contains("win")
                ? "it-timeout-test.cmd"
                : "it-timeout-test.sh";
    }

    private long uploadSleepScript(String token) throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file", sleepFilename(), "text/plain",
                sleepContent().getBytes(StandardCharsets.UTF_8));

        MvcResult result = mockMvc.perform(multipart("/api/scripts")
                        .file(file)
                        .param("name", "it-sleep-" + System.nanoTime())
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andReturn();

        return objectMapper.readTree(result.getResponse().getContentAsString())
                .path("id").asLong();
    }

    private JsonNode waitForTerminal(String token, long executionId) throws Exception {
        long deadline = System.currentTimeMillis() + 20_000;
        while (System.currentTimeMillis() < deadline) {
            String body = mockMvc.perform(get("/api/executions/{id}", executionId)
                            .header("Authorization", "Bearer " + token))
                    .andExpect(status().isOk())
                    .andReturn().getResponse().getContentAsString();
            JsonNode node = objectMapper.readTree(body);
            if (!"RUNNING".equals(node.path("status").asText())) {
                return node;
            }
            Thread.sleep(200);
        }
        throw new AssertionError("Execution did not finish in time");
    }

    @Test
    void scriptEndToEndExecutesSuccessfully() throws Exception {
        String token = loginAdmin();
        long scriptId = uploadScript(token);

        String execBody = objectMapper.writeValueAsString(
                new ExecuteRequest(java.util.Map.of(), java.util.Map.of(), 60, "NEVER"));
        MvcResult execResult = mockMvc.perform(post("/api/scripts/{id}/execute", scriptId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(execBody)
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isAccepted())
                .andReturn();

        long executionId = objectMapper.readTree(execResult.getResponse().getContentAsString())
                .path("id").asLong();

        JsonNode terminal = waitForTerminal(token, executionId);
        assertThat(terminal.path("status").asText()).isEqualTo("SUCCESS");
        assertThat(terminal.path("exitCode").asInt()).isEqualTo(0);

        String log = mockMvc.perform(get("/api/executions/{id}/log", executionId)
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();

        assertThat(log).contains("hello-autorun-test");
    }

    @Test
    void scriptTimesOutWhenExceedingTimeout() throws Exception {
        String token = loginAdmin();
        long scriptId = uploadSleepScript(token);

        String execBody = objectMapper.writeValueAsString(
                new ExecuteRequest(java.util.Map.of(), java.util.Map.of(), 1, "NEVER"));
        MvcResult execResult = mockMvc.perform(post("/api/scripts/{id}/execute", scriptId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(execBody)
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isAccepted())
                .andReturn();

        long executionId = objectMapper.readTree(execResult.getResponse().getContentAsString())
                .path("id").asLong();

        JsonNode terminal = waitForTerminal(token, executionId);
        assertThat(terminal.path("status").asText()).isEqualTo("TIMEOUT");
    }

    @Test
    void unauthenticatedExecutionReturns401() throws Exception {
        mockMvc.perform(post("/api/scripts/99999/execute"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void listExecutionsRequiresAuth() throws Exception {
        mockMvc.perform(get("/api/executions"))
                .andExpect(status().isUnauthorized());
    }

    private record LoginRequest(String username, String password) {}
    private record ExecuteRequest(java.util.Map<String, String> arguments,
                                  java.util.Map<String, String> env,
                                  Integer timeoutSeconds,
                                  String notifyOn) {}
}
