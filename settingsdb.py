""" Library for interacting with the Guild Settings DB easily """
import sqlite3


class SettingsDB:
    """ Class for interacting with the Guild Settings DB """
    def __init__(self):
        self.connection = sqlite3.connect("settings.db")
        self.cursor = self.connection.cursor()

        self.cursor.execute("CREATE TABLE IF NOT EXISTS settings (guild_id INTEGER PRIMARY KEY, settings TEXT)")

    def get_settings(self, guild_id: int):
        """ Get guild settings """
        self.cursor.execute("SELECT settings FROM settings WHERE guild_id = ?", (guild_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            return None

    def set_settings(self, guild_id: int, settings: str):
        """ Set guild settings """
        self.cursor.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (guild_id, settings))
        self.connection.commit()

    def close(self):
        """ Close the connection """
        self.connection.close()

    def __del__(self):
        self.close()
