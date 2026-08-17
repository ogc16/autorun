package com.autorun;

import com.autorun.repository.ScriptRepository;
import com.autorun.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.ResponseEntity;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AutoRunApplicationTests {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private ScriptRepository scriptRepository;

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    void contextLoadsAndSeedsData() {
        assertThat(userRepository.findByUsername("admin")).isPresent();
        assertThat(userRepository.findByUsername("tech")).isPresent();
        assertThat(scriptRepository.count()).isGreaterThanOrEqualTo(5);
    }

    @Test
    void healthEndpointReturnsHealthInfo() {
        ResponseEntity<String> response = restTemplate.getForEntity("/actuator/health", String.class);
        assertThat(response.getBody()).contains("\"status\"");
    }
}
