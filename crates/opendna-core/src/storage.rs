use crate::models::Protein;
use rusqlite::{params, Connection, Result};
use std::path::Path;

pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn open(path: &Path) -> Result<Self> {
        let conn = Connection::open(path)?;
        let db = Self { conn };
        db.init_tables()?;
        Ok(db)
    }

    pub fn open_in_memory() -> Result<Self> {
        let conn = Connection::open_in_memory()?;
        let db = Self { conn };
        db.init_tables()?;
        Ok(db)
    }

    fn init_tables(&self) -> Result<()> {
        self.conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS proteins (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sequence TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                input TEXT NOT NULL,
                output TEXT,
                progress REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
            ",
        )?;
        Ok(())
    }

    pub fn save_protein(&self, protein: &Protein) -> Result<()> {
        let metadata = serde_json::to_string(&protein.metadata).unwrap_or_default();
        self.conn.execute(
            "INSERT OR REPLACE INTO proteins (id, name, sequence, metadata, created_at, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                protein.id,
                protein.name,
                protein.sequence.residues,
                metadata,
                protein.created_at.to_rfc3339(),
                protein.updated_at.to_rfc3339(),
            ],
        )?;
        Ok(())
    }

    pub fn get_protein(&self, id: &str) -> Result<Option<Protein>> {
        let mut stmt = self
            .conn
            .prepare("SELECT id, name, sequence, metadata, created_at, updated_at FROM proteins WHERE id = ?1")?;

        let result = stmt.query_row(params![id], |row| {
            let sequence: String = row.get(2)?;
            let metadata_str: String = row.get(3)?;
            let created_str: String = row.get(4)?;
            let updated_str: String = row.get(5)?;

            Ok(Protein {
                id: row.get(0)?,
                name: row.get(1)?,
                sequence: crate::models::Sequence::new(sequence),
                structure: None,
                metadata: serde_json::from_str(&metadata_str).unwrap_or_default(),
                created_at: chrono::DateTime::parse_from_rfc3339(&created_str)
                    .unwrap()
                    .with_timezone(&chrono::Utc),
                updated_at: chrono::DateTime::parse_from_rfc3339(&updated_str)
                    .unwrap()
                    .with_timezone(&chrono::Utc),
            })
        });

        match result {
            Ok(protein) => Ok(Some(protein)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e),
        }
    }

    pub fn list_proteins(&self) -> Result<Vec<(String, String, usize)>> {
        let mut stmt = self
            .conn
            .prepare("SELECT id, name, sequence FROM proteins ORDER BY created_at DESC")?;

        let results = stmt
            .query_map([], |row| {
                let seq: String = row.get(2)?;
                Ok((row.get(0)?, row.get(1)?, seq.len()))
            })?
            .collect::<Result<Vec<_>>>()?;

        Ok(results)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_database_roundtrip() {
        let db = Database::open_in_memory().unwrap();
        let protein = Protein::new("Test", "MKTVRQERLK");
        let id = protein.id.clone();

        db.save_protein(&protein).unwrap();
        let loaded = db.get_protein(&id).unwrap().unwrap();

        assert_eq!(loaded.name, "Test");
        assert_eq!(loaded.sequence.residues, "MKTVRQERLK");
    }

    #[test]
    fn test_list_proteins() {
        let db = Database::open_in_memory().unwrap();
        db.save_protein(&Protein::new("P1", "MKTV")).unwrap();
        db.save_protein(&Protein::new("P2", "ACDE")).unwrap();

        let list = db.list_proteins().unwrap();
        assert_eq!(list.len(), 2);
    }
}
