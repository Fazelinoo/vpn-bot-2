module.exports = {
  apps: [
    {
      name: "vpn-bot",
      script: "main.py",
      interpreter: "./venv/bin/python",
      cwd: "/opt/vpn-bot",
      autorestart: true,
      watch: false,
      max_memory_restart: "256M",
      env: {
        NODE_ENV: "production",
      },
      error_file: "./logs/pm2-error.log",
      out_file: "./logs/pm2-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
    },
  ],
};
