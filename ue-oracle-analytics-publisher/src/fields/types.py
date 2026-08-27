"""UAC field type definitions for type-safe field handling."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, Dict
import json


@dataclass
class Credential:
    """UAC Credential field type.

    Represents a credential field with structured access to credential components.
    UAC flattens credentials into dotted notation (e.g., "api_credential.user"),
    but this provides a structured interface.

    Usage:
        cred = Credential(user="myuser", password="pass", token="abc123")
        print(cred.user)  # "myuser"
        print(cred.password)  # "pass"
        print(cred.token)  # "abc123"
    """

    user: str
    password: Optional[str] = None
    token: Optional[str] = None
    passphrase: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Credential":
        """Create Credential from dictionary (UAC provides as dict).

        Args:
            data: Dictionary with credential fields

        Returns:
            Credential instance
        """
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class Text:
    """UAC Text field type.

    Simple text field wrapper with optional JSON/YAML parsing.
    Used in output fields and can be used in input fields.

    Usage:
        text = Text("Hello World")
        print(text)  # "Hello World"
        print(text.value)  # "Hello World"

        # JSON validation/parsing
        json_text = Text('{"key": "value"}')
        json_text.validate_json()  # Raises ValueError if invalid
        data = json_text.parse_json()  # {"key": "value"}

        # YAML validation/parsing
        yaml_text = Text('key: value')
        yaml_text.validate_yaml()  # Raises ValueError if invalid
        data = yaml_text.parse_yaml()  # {"key": "value"}
    """

    value: str

    def validate_json(self) -> None:
        """Validate that value is valid JSON.

        Raises:
            ValueError: If value is not valid JSON
        """
        try:
            json.loads(self.value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def parse_json(self) -> Dict[str, Any]:
        """Parse value as JSON and return dictionary.

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If value is not valid JSON
        """
        try:
            return json.loads(self.value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def validate_yaml(self) -> None:
        """Validate that value is valid YAML.

        Raises:
            ValueError: If value is not valid YAML
            ImportError: If PyYAML is not installed
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML not installed. Add 'pyyaml' to requirements.txt")
        try:
            yaml.safe_load(self.value)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

    def parse_yaml(self) -> Dict[str, Any]:
        """Parse value as YAML and return dictionary.

        Returns:
            Parsed YAML as dictionary

        Raises:
            ValueError: If value is not valid YAML
            ImportError: If PyYAML is not installed
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML not installed. Add 'pyyaml' to requirements.txt")
        try:
            return yaml.safe_load(self.value)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

    def __str__(self) -> str:
        """Return text value."""
        return self.value

    def __repr__(self) -> str:
        """Return representation."""
        return f"Text({self.value!r})"


@dataclass
class Script:
    """UAC Script field type.

    Represents a script field which UAC provides as a temporary file path.
    Provides helper methods to read and parse the script content.

    Usage:
        script = Script(Path("/tmp/query.sql"))
        content = script.read()
        data = script.read_json()  # if JSON content
    """

    path: Path

    def read(self) -> str:
        """Read script file content as text.

        Returns:
            Script content as string

        Raises:
            FileNotFoundError: If script file doesn't exist
            IOError: If script file cannot be read
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Script file not found: {self.path}")
        return self.path.read_text()

    def read_json(self) -> Dict[str, Any]:
        """Read and parse script content as JSON.

        Returns:
            Parsed JSON as dictionary

        Raises:
            json.JSONDecodeError: If content is not valid JSON
        """
        content = self.read()
        return json.loads(content)

    def read_yaml(self) -> Dict[str, Any]:
        """Read and parse script content as YAML.

        Returns:
            Parsed YAML as dictionary

        Raises:
            yaml.YAMLError: If content is not valid YAML
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML not installed. Add 'pyyaml' to requirements.txt")
        content = self.read()
        return yaml.safe_load(content)

    def exists(self) -> bool:
        """Check if script file exists.

        Returns:
            True if file exists, False otherwise
        """
        return self.path.exists()


@dataclass
class Integer:
    """UAC Integer field type.

    For whole number inputs (ports, timeouts, counts, IDs).
    Provides type-safe integer handling with optional range validation.

    Usage:
        port = Integer(8080, min_value=1024, max_value=65535)
        print(port.value)  # 8080
        port.validate()  # Raises ValueError if out of range
    """

    value: int
    min_value: Optional[int] = None
    max_value: Optional[int] = None

    def validate(self) -> None:
        """Validate integer is within specified range.

        Raises:
            ValueError: If value is outside min/max bounds
        """
        if self.min_value is not None and self.value < self.min_value:
            raise ValueError(f"Value {self.value} is below minimum {self.min_value}")
        if self.max_value is not None and self.value > self.max_value:
            raise ValueError(f"Value {self.value} exceeds maximum {self.max_value}")

    def __int__(self) -> int:
        """Return integer value."""
        return self.value

    def __str__(self) -> str:
        """Return string representation."""
        return str(self.value)


@dataclass
class Float:
    """UAC Float field type.

    For decimal number inputs (percentages, rates, measurements).
    Provides type-safe float handling.

    Usage:
        rate = Float(3.14)
        print(rate.value)  # 3.14
    """

    value: float

    def __float__(self) -> float:
        """Return float value."""
        return self.value

    def __str__(self) -> str:
        """Return string representation."""
        return str(self.value)


@dataclass
class Boolean:
    """UAC Boolean field type.

    For yes/no toggles, enable/disable switches.
    Provides type-safe boolean handling.

    Usage:
        use_ssl = Boolean(True)
        if use_ssl:  # Can use directly in conditionals
            ...
    """

    value: bool

    def __bool__(self) -> bool:
        """Return boolean value for conditional checks."""
        return self.value

    def __str__(self) -> str:
        """Return string representation."""
        return str(self.value)


@dataclass
class SingleChoice:
    """UAC Single-selection Choice field type.

    For dropdown fields where only one option can be selected (choiceAllowMultiple=false).
    UAC returns single choices as a list with one element.

    Usage:
        action = SingleChoice(["create"])
        print(action.value)  # "create"
        print(action)  # "create"
        if action == "create":  # Compare directly
            ...
    """

    _values: list[str]

    @property
    def value(self) -> Optional[str]:
        """Get the selected value.

        Returns:
            Selected value or None if empty
        """
        return self._values[0] if self._values else None

    def is_empty(self) -> bool:
        """Check if no selection was made.

        Returns:
            True if no value selected, False otherwise
        """
        return len(self._values) == 0

    def __eq__(self, other) -> bool:
        """Compare choice value with string.

        Args:
            other: Value to compare

        Returns:
            True if selected value matches
        """
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

    def __str__(self) -> str:
        """Return string representation."""
        return self.value if self.value else "(none)"


@dataclass
class MultiChoice:
    """UAC Multi-selection Choice field type.

    For dropdown fields where multiple options can be selected (choiceAllowMultiple=true).
    UAC returns multi choices as a list of selected values.

    Usage:
        options = MultiChoice(["opt1", "opt2"])
        print(options.values)  # ["opt1", "opt2"]
        print("opt1" in options)  # True
        for value in options:
            print(value)
    """

    values: list[str]

    def is_empty(self) -> bool:
        """Check if no selections were made.

        Returns:
            True if no values selected, False otherwise
        """
        return len(self.values) == 0

    def __contains__(self, item: str) -> bool:
        """Check if value is in selection.

        Args:
            item: Value to check

        Returns:
            True if item is selected, False otherwise
        """
        return item in self.values

    def __iter__(self):
        """Iterate over selected values."""
        return iter(self.values)

    def __len__(self) -> int:
        """Return number of selected values."""
        return len(self.values)

    def __str__(self) -> str:
        """Return string representation."""
        return ", ".join(self.values) if self.values else "(none)"

@dataclass
class Array:
    """UAC Array field type.

    For key-value pairs, headers, parameters.
    UAC returns arrays as single-key dictionaries: [{"key": "value"}]

    IMPORTANT: UAC transforms array fields from the task definition format:
        {"name": "X", "value": "Y"}
    Into flattened single-key objects:
        {"X": "Y"}

    This class handles UAC's flattened format.

    Usage:
        # UAC sends: [{"Content-Type": "application/json"}, {"Authorization": "Bearer token"}]
        headers = Array([
            {"Content-Type": "application/json"},
            {"Authorization": "Bearer token"}
        ])

        print(headers.get("Content-Type"))  # "application/json"
        for name, value in headers.items():
            print(f"{name}: {value}")
    """

    pairs: list[dict[str, str]]

    def _extract_pair(self, pair: dict[str, str]) -> tuple[str, str]:
        """Extract name and value from a flattened pair dict.

        Args:
            pair: Single-key dictionary {"key": "value"}

        Returns:
            Tuple of (name, value)
        """
        # UAC sends single-key objects: {"key": "value"}
        if pair:
            name, value = next(iter(pair.items()))
            return str(name), str(value)
        return "", ""

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get value for a specific name/key.

        Args:
            name: Key name to look up
            default: Default value if key not found

        Returns:
            Value for the key or default if not found
        """
        for pair in self.pairs:
            pair_name, pair_value = self._extract_pair(pair)
            if pair_name == name:
                return pair_value if pair_value else default
        return default

    def items(self) -> list[tuple[str, str]]:
        """Get list of (name, value) tuples.

        Returns:
            List of tuples with name-value pairs
        """
        return [self._extract_pair(pair) for pair in self.pairs]

    def to_dict(self) -> dict[str, str]:
        """Convert array to dictionary.

        Returns:
            Dictionary mapping names to values
        """
        return {name: value for name, value in self.items()}

    def __len__(self) -> int:
        """Return number of pairs."""
        return len(self.pairs)

    def __str__(self) -> str:
        """Return string representation."""
        return str(self.to_dict())