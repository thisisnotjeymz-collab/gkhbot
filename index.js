const { Client, GatewayIntentBits } = require("discord.js");

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

const autoResponses = [
  {
    trigger: "hello",
    response: "hellow",
  },
  {
    trigger: "burat",
    response: "mahilig ka siguro sa burat",
  },
  {
    trigger: "help",
    response: "open a ticket sa desk if may concern ka",
  },
    },
  {
    trigger: "ulol",
    response: "ulol mo blue",
  },
    },
  {
    trigger: "tangina",
    response: "tangina mo din",
  },
    },
  {
    trigger: "bobo",
    response: "mas bobo ka",
  },
];

client.once("ready", () => {
  console.log(`Logged in as ${client.user.tag}`);
});

client.on("messageCreate", async (message) => {
  if (message.author.bot) return;
  if (!message.guild) return;

  const content = message.content.toLowerCase();

  for (const ar of autoResponses) {
    const regex = new RegExp(`\\b${ar.trigger}\\b`, "i");

    if (regex.test(content)) {
      await message.reply(ar.response);
      break;
    }
  }
});

client.login(process.env.TOKEN);
