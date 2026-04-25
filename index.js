const { Client, GatewayIntentBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ChannelType, PermissionsBitField } = require('discord.js');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Initialize Discord Client
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds, 
        GatewayIntentBits.GuildMessages, 
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers
    ]
});

// Helper to read/write config
const getConfig = () => JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
const saveConfig = (data) => fs.writeFileSync(path.join(__dirname, 'config.json'), JSON.stringify(data, null, 2));

// --- ANIME NOTIFIER ---
const API_URL = process.env.API_URL || "http://localhost:3000/api/newadded";
const STATE_FILE = path.join(__dirname, 'last_seen.json');
let lastSeenId = fs.existsSync(STATE_FILE) ? JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')).lastSeenId : null;

async function checkForNewEpisodes() {
    const config = getConfig();
    if (!config.announcementChannel) return;

    try {
        const channel = await client.channels.fetch(config.announcementChannel).catch(() => null);
        if (!channel) return;

        const response = await axios.get(API_URL);
        if (!response.data.success || !response.data.results) return;

        const latestEpisodes = response.data.results;
        const newEpisodes = [];
        for (const ep of latestEpisodes) {
            const uniqueId = `${ep.anime_id}-s${ep.season}-e${ep.episode}`;
            if (uniqueId === lastSeenId) break;
            newEpisodes.unshift(ep);
        }

        if (newEpisodes.length > 0) {
            for (const ep of newEpisodes) {
                const embed = new EmbedBuilder()
                    .setTitle(`New Episode Released: ${ep.title}`)
                    .setDescription(`**Season:** ${ep.season} | **Episode:** ${ep.episode}`)
                    .setColor('#FF4500')
                    .setImage(ep.poster || null)
                    .setFooter({ text: 'KagePlay Anime Bot' })
                    .setTimestamp();

                const pingText = config.pingRole ? `<@&${config.pingRole}>` : '';
                await channel.send({ content: `${pingText} A new episode is out!`, embeds: [embed] });
                
                lastSeenId = `${ep.anime_id}-s${ep.season}-e${ep.episode}`;
                fs.writeFileSync(STATE_FILE, JSON.stringify({ lastSeenId }));
            }
        }
    } catch (err) {
        console.error("Anime Checker Error:", err.message);
    }
}

// --- DISCORD EVENTS ---

client.once('ready', () => {
    console.log(`Bot Logged in as ${client.user.tag}!`);
    setInterval(checkForNewEpisodes, 5 * 60 * 1000);
    
    // Start Web Dashboard
    require('./dashboard')(client, getConfig, saveConfig);
});

// Welcome Message
client.on('guildMemberAdd', async (member) => {
    const config = getConfig();
    if (config.welcomeChannel && config.welcomeMessage) {
        const channel = member.guild.channels.cache.get(config.welcomeChannel);
        if (channel) {
            const msg = config.welcomeMessage.replace('{user}', `<@${member.id}>`);
            
            let gifUrl = null;
            const reaction = config.welcomeReaction || 'celebrate'; // Default reaction
            try {
                const response = await axios.get(`https://api.otakugifs.xyz/gif?reaction=${reaction}&format=gif`);
                if (response.data && response.data.url) {
                    gifUrl = response.data.url;
                }
            } catch (err) {
                console.error("Failed to fetch OtakuGIF:", err.message);
            }

            if (gifUrl) {
                const embed = new EmbedBuilder()
                    .setDescription(msg)
                    .setImage(gifUrl)
                    .setColor('#00FF00');
                channel.send({ content: `<@${member.id}>`, embeds: [embed] });
            } else {
                channel.send(msg);
            }
        }
    }
});

// Leave Message
client.on('guildMemberRemove', async (member) => {
    const config = getConfig();
    if (config.leaveChannel && config.leaveMessage) {
        const channel = member.guild.channels.cache.get(config.leaveChannel);
        if (channel) {
            const msg = config.leaveMessage.replace('{user}', `**${member.user.tag}**`);
            channel.send(msg);
        }
    }
});

// Simple command to spawn ticket panel
client.on('messageCreate', async (message) => {
    if (message.content === '!setuptickets' && message.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
        const embed = new EmbedBuilder()
            .setTitle('Support Tickets')
            .setDescription('Click the button below to open a support ticket.')
            .setColor('#0099ff');
        
        const row = new ActionRowBuilder().addComponents(
            new ButtonBuilder().setCustomId('create_ticket').setLabel('🎫 Create Ticket').setStyle(ButtonStyle.Primary)
        );

        await message.channel.send({ embeds: [embed], components: [row] });
        message.delete();
    }
});

// Button Interactions (Tickets)
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;
    const config = getConfig();

    if (interaction.customId === 'create_ticket') {
        const ticketChannelName = `ticket-${interaction.user.username.toLowerCase()}`;
        
        // Check if ticket already exists
        const existingChannel = interaction.guild.channels.cache.find(c => c.name === ticketChannelName);
        if (existingChannel) {
            return interaction.reply({ content: `You already have a ticket open: ${existingChannel}`, ephemeral: true });
        }

        // Create Channel
        const channel = await interaction.guild.channels.create({
            name: ticketChannelName,
            type: ChannelType.GuildText,
            parent: config.ticketCategory || null,
            permissionOverwrites: [
                { id: interaction.guild.id, deny: [PermissionsBitField.Flags.ViewChannel] },
                { id: interaction.user.id, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] },
                { id: client.user.id, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] }
            ]
        });

        const embed = new EmbedBuilder()
            .setTitle('Support Ticket')
            .setDescription(`Hello <@${interaction.user.id}>, please describe your issue here. Support will be with you shortly.`)
            .setColor('#00FF00');

        const row = new ActionRowBuilder().addComponents(
            new ButtonBuilder().setCustomId('close_ticket').setLabel('🔒 Close Ticket').setStyle(ButtonStyle.Danger)
        );

        await channel.send({ content: `<@${interaction.user.id}>`, embeds: [embed], components: [row] });
        await interaction.reply({ content: `Ticket created! ${channel}`, ephemeral: true });
    }

    if (interaction.customId === 'close_ticket') {
        await interaction.reply('Closing ticket in 5 seconds...');
        setTimeout(() => interaction.channel.delete(), 5000);
    }
});

client.login(process.env.DISCORD_TOKEN);
