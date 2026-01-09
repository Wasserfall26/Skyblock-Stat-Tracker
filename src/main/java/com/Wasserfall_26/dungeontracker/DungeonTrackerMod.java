package com.Wasserfall_26.dungeontracker;

import net.minecraft.client.Minecraft;
import net.minecraft.client.settings.KeyBinding;
import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.event.ClickEvent;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.ChatStyle;
import net.minecraft.util.IChatComponent;
import net.minecraftforge.client.ClientCommandHandler;
import net.minecraftforge.client.event.ClientChatReceivedEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.client.registry.ClientRegistry;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.fml.common.event.FMLPreInitializationEvent;
import net.minecraftforge.fml.common.eventhandler.EventPriority;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.fml.common.gameevent.InputEvent;
import net.minecraftforge.fml.common.gameevent.TickEvent;
import org.lwjgl.input.Keyboard;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.LinkedList;
import java.util.Queue;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Mod(modid = DungeonTrackerMod.MODID, version = DungeonTrackerMod.VERSION, name = DungeonTrackerMod.NAME)
public class DungeonTrackerMod {
    public static final String MODID = "dungeontracker";
    public static final String VERSION = "1.0";
    public static final String NAME = "SkyBlock Tracker";

    private static final Pattern PLAYER_NAME_PATTERN = Pattern.compile("\\b([A-Za-z0-9_]{3,16})\\b");

    private KeyBinding openTrackerKey;
    private Process currentProcess = null;
    private File pythonScriptFile;
    private File dataFile;

    // Queue for commands to execute
    private Queue<String> pendingCommands = new LinkedList<>();

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        // Extract Python script from JAR to config folder
        File configDir = new File(event.getModConfigurationDirectory(), "dungeontracker");
        if (!configDir.exists()) {
            configDir.mkdirs();
        }

        // UPDATED: Look for skyblock_tracker.py instead of skyblock.py
        pythonScriptFile = new File(configDir, "skyblock_tracker.py");
        dataFile = new File(configDir, "recent_players.json");

        // Extract script from JAR
        try {
            // UPDATED: Resource path changed to skyblock_tracker.py
            InputStream scriptStream = getClass().getResourceAsStream("/assets/dungeontracker/skyblock_tracker.py");
            if (scriptStream != null) {
                Files.copy(scriptStream, pythonScriptFile.toPath(), StandardCopyOption.REPLACE_EXISTING);
                scriptStream.close();
                System.out.println("[SkyBlock Tracker] Extracted Python script to: " + pythonScriptFile.getAbsolutePath());
            } else {
                System.err.println("[SkyBlock Tracker] ERROR: Could not find skyblock_tracker.py in JAR!");
            }
        } catch (IOException e) {
            System.err.println("[SkyBlock Tracker] Failed to extract Python script:");
            e.printStackTrace();
        }
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        // Register keybinding (default: P)
        openTrackerKey = new KeyBinding("Open SkyBlock Tracker", Keyboard.KEY_P, "SkyBlock Tracker");
        ClientRegistry.registerKeyBinding(openTrackerKey);

        // Register event handlers
        MinecraftForge.EVENT_BUS.register(this);

        // UPDATED: Register new command /stopen
        ClientCommandHandler.instance.registerCommand(new CommandSTOpen());

        System.out.println("[SkyBlock Tracker] Mod initialized!");
        System.out.println("[SkyBlock Tracker] Python script location: " + pythonScriptFile.getAbsolutePath());
    }

    /**
     * Client-side command to open tracker
     * UPDATED: Command name changed from /dtopen to /stopen
     * CRITICAL: Only executes if ALT is held at the moment of execution
     */
    private class CommandSTOpen extends CommandBase {
        @Override
        public String getCommandName() {
            return "stopen";
        }

        @Override
        public String getCommandUsage(ICommandSender sender) {
            return "/stopen <playername>";
        }

        @Override
        public void processCommand(ICommandSender sender, String[] args) {
            if (args.length > 0) {
                String playerName = args[0];

                // Check if ALT is held (for click events)
                boolean altHeld = Keyboard.isKeyDown(Keyboard.KEY_LMENU) || Keyboard.isKeyDown(Keyboard.KEY_RMENU);

                // Check if command was typed manually (sender is the player)
                boolean isManualCommand = sender == Minecraft.getMinecraft().thePlayer;

                if (altHeld || isManualCommand) {
                    pendingCommands.add(playerName);
                    System.out.println("[SkyBlock Tracker] Opening tracker for: " + playerName);

                    // Show feedback for manual commands
                    if (isManualCommand && !altHeld) {
                        Minecraft.getMinecraft().thePlayer.addChatMessage(
                                new ChatComponentText("§a[SkyBlock Tracker] Opening tracker for §b" + playerName + "§a...")
                        );
                    }
                } else {
                    System.out.println("[SkyBlock Tracker] ALT not held - ignoring click on: " + playerName);
                    // Silently ignore - no feedback to user
                }
            } else {
                // No argument - show usage
                Minecraft.getMinecraft().thePlayer.addChatMessage(
                        new ChatComponentText("§c[SkyBlock Tracker] Usage: /stopen <playername>")
                );
            }
        }

        @Override
        public int getRequiredPermissionLevel() {
            return 0;
        }

        @Override
        public boolean canCommandSenderUseCommand(ICommandSender sender) {
            return true;
        }

        @Override
        public boolean isUsernameIndex(String[] args, int index) {
            return false;
        }
    }

    @SubscribeEvent
    public void onKeyInput(InputEvent.KeyInputEvent event) {
        // Open tracker without player name when P is pressed (not in chat)
        if (openTrackerKey.isPressed() && Minecraft.getMinecraft().currentScreen == null) {
            openTracker(null);
        }
    }

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        // Process pending commands on client tick
        if (event.phase == TickEvent.Phase.END && !pendingCommands.isEmpty()) {
            String playerName = pendingCommands.poll();
            if (playerName != null) {
                openTracker(playerName);
            }
        }
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public void onChatReceived(ClientChatReceivedEvent event) {
        // Get the original message component (preserves all formatting)
        IChatComponent originalMessage = event.message;
        String unformattedMessage = originalMessage.getUnformattedText();

        // Split message by spaces and special characters to get individual words
        String[] words = unformattedMessage.split("[\\s\\[\\]():><!]+");

        // Find player names only in isolated words
        boolean foundAnyName = false;
        for (String word : words) {
            // Check if this word looks like a username (3-16 chars, alphanumeric + underscore)
            if (word.matches("[A-Za-z0-9_]{3,16}")) {
                // Additional check: ignore common words
                if (!isCommonWord(word)) {
                    foundAnyName = true;
                    addClickEventToWord(originalMessage, word);
                }
            }
        }

        if (!foundAnyName) {
            return; // No valid player names found
        }
    }

    /**
     * Check if a word is a common word (not a player name)
     */
    private boolean isCommonWord(String word) {
        String lower = word.toLowerCase();
        return lower.equals("party") || lower.equals("finder") || lower.equals("joined") ||
                lower.equals("left") || lower.equals("the") || lower.equals("dungeon") ||
                lower.equals("group") || lower.equals("level") || lower.equals("has") ||
                lower.equals("been") || lower.equals("queued") || lower.equals("your") ||
                lower.equals("from") || lower.equals("to") || lower.equals("archer") ||
                lower.equals("mage") || lower.equals("berserk") || lower.equals("healer") ||
                lower.equals("tank") || lower.equals("mvp") || lower.equals("vip");
    }

    /**
     * Add click event to a specific word in the message
     */
    private void addClickEventToWord(IChatComponent component, String targetWord) {
        String componentText = component.getUnformattedText();

        // Check if this component contains the target word (as a standalone word)
        if (componentText.contains(targetWord)) {
            // Add click event to existing style
            ChatStyle style = component.getChatStyle();
            if (style == null) {
                style = new ChatStyle();
            }

            style.setChatClickEvent(new ClickEvent(
                    ClickEvent.Action.RUN_COMMAND,
                    "/stopen " + targetWord
            ));

            component.setChatStyle(style);
        }

        // Recursively check all sibling components
        for (IChatComponent sibling : component.getSiblings()) {
            addClickEventToWord(sibling, targetWord);
        }
    }

    /**
     * Open the tracker with optional player name
     */
    public void openTracker(String playerName) {
        try {
            // Close existing process if any
            if (currentProcess != null && currentProcess.isAlive()) {
                currentProcess.destroy();
                Thread.sleep(100);
            }

            if (!pythonScriptFile.exists()) {
                Minecraft.getMinecraft().thePlayer.addChatMessage(
                        new ChatComponentText("§c[SkyBlock Tracker] Error: Python script not found!")
                );
                System.err.println("[SkyBlock Tracker] Script not found at: " + pythonScriptFile.getAbsolutePath());
                return;
            }

            // Build command
            ProcessBuilder pb;
            if (playerName != null && !playerName.isEmpty()) {
                pb = new ProcessBuilder("python", pythonScriptFile.getAbsolutePath(), playerName);
            } else {
                pb = new ProcessBuilder("python", pythonScriptFile.getAbsolutePath());
            }

            // Set working directory to config folder
            pb.directory(pythonScriptFile.getParentFile());
            pb.redirectErrorStream(true);

            // Start process
            currentProcess = pb.start();

            System.out.println("[SkyBlock Tracker] Opened tracker" +
                    (playerName != null ? " for player: " + playerName : ""));

            // Show confirmation in chat
            if (Minecraft.getMinecraft().thePlayer != null) {
                Minecraft.getMinecraft().thePlayer.addChatMessage(
                        new ChatComponentText("§a[SkyBlock Tracker] Opening tracker" +
                                (playerName != null ? " for §b" + playerName : "") + "...")
                );
            }

        } catch (IOException e) {
            e.printStackTrace();
            if (Minecraft.getMinecraft().thePlayer != null) {
                Minecraft.getMinecraft().thePlayer.addChatMessage(
                        new ChatComponentText("§c[SkyBlock Tracker] Error: " + e.getMessage())
                );
                Minecraft.getMinecraft().thePlayer.addChatMessage(
                        new ChatComponentText("§c[SkyBlock Tracker] Make sure Python is installed and in PATH!")
                );
            }
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    /**
     * Check if player is on Hypixel
     */
    private boolean isOnHypixel() {
        try {
            if (Minecraft.getMinecraft().getCurrentServerData() != null) {
                String serverIP = Minecraft.getMinecraft().getCurrentServerData().serverIP.toLowerCase();
                return serverIP.contains("hypixel.net") || serverIP.contains("hypixel.io");
            }
        } catch (Exception e) {
            // Ignore
        }
        return false;
    }
}