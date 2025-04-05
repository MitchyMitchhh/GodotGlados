# EMERGENCY-HOTFIX PROJECT STANDARDS
# Always reference these rules when writing or modifying code

# CODING STYLE
- Always use tabs for indentation, never spaces
- Maximum line length is 100 characters
- Variable names use snake_case
- Constants should be ALL_CAPS
- Class names use PascalCase
- Always add typing to function parameters and return values
- Comments should explain "why", not "what" use minimal comments.

# GAME ARCHITECTURE
- This game is a limb based multiplayer (both local and multiplayer) 2d arena battle game. Similar games in the intended genre are "ROUNDS" "Duck Game", "Bopl Battle", "SpiderHeck" 
- Each player can equip a weapon on each the front and back arms and can use those weapons if the arms are not destroyed.
- After a round ends when only one player remains, the player that remains will be selected for a nerf/debuff option select screen that the other players can vote on. These nerfs persist on the player through later rounds until the game is over

# PERFORMANCE GUIDELINES
- Avoid creating objects in _process or _physics_process
- Cache node references with @onready var
- Use object pooling for frequently spawned objects (bullets, effects)
- Prefer 2D physics for gameplay mechanics
