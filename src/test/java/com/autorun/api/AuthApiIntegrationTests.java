package com.autorun.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class AuthApiIntegrationTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    private String login(String username, String password) throws Exception {
        String body = objectMapper.writeValueAsString(new LoginRequest(username, password));
        MvcResult result = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andReturn();
        JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
        return json.path("accessToken").asText();
    }

    @Test
    void unauthenticatedAccessReturns401() throws Exception {
        mockMvc.perform(get("/api/scripts"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void loginWithValidCredentialsReturnsToken() throws Exception {
        String token = login("admin", "admin123");
        org.assertj.core.api.Assertions.assertThat(token).isNotBlank();
    }

    @Test
    void loginWithBadCredentialsReturns401() throws Exception {
        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"wrong\"}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void authenticatedUserCanListScripts() throws Exception {
        String token = login("admin", "admin123");
        mockMvc.perform(get("/api/scripts")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());
    }

    @Test
    void authenticatedUserCanFetchProfile() throws Exception {
        String token = login("admin", "admin123");
        mockMvc.perform(get("/api/auth/me")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());
    }

    @Test
    void techRoleForbiddenFromAdminEndpoint() throws Exception {
        String token = login("tech", "tech123");
        mockMvc.perform(get("/api/users")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isForbidden());
    }

    @Test
    void adminCanAccessAdminEndpoint() throws Exception {
        String token = login("admin", "admin123");
        mockMvc.perform(get("/api/users")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());
    }

    @Test
    void refreshTokenReturnsNewTokens() throws Exception {
        String loginBody = objectMapper.writeValueAsString(new LoginRequest("admin", "admin123"));
        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginBody))
                .andExpect(status().isOk())
                .andReturn();
        String refreshToken = objectMapper.readTree(loginResult.getResponse().getContentAsString())
                .path("refreshToken").asText();

        String refreshBody = objectMapper.writeValueAsString(new RefreshRequest(refreshToken));
        mockMvc.perform(post("/api/auth/refresh")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(refreshBody))
                .andExpect(status().isOk());
    }

    @Test
    void refreshWithInvalidTokenReturns401() throws Exception {
        String body = objectMapper.writeValueAsString(new RefreshRequest("invalid.token.here"));
        mockMvc.perform(post("/api/auth/refresh")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isUnauthorized());
    }

    private record LoginRequest(String username, String password) {}
    private record RefreshRequest(String refreshToken) {}
}
