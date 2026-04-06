use crate::models::Protein;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A single version of a protein in the version history.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProteinVersion {
    pub id: String,
    pub protein: Protein,
    pub parent_id: Option<String>,
    pub mutations: Vec<Mutation>,
    pub message: String,
    pub author: String,
    pub timestamp: DateTime<Utc>,
}

/// A mutation that was applied to create this version.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Mutation {
    pub position: usize,
    pub from: char,
    pub to: char,
    pub reason: Option<String>,
}

impl std::fmt::Display for Mutation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}{}{}", self.from, self.position + 1, self.to)
    }
}

/// A named branch pointing to a version.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProteinBranch {
    pub name: String,
    pub head_id: String,
    pub description: String,
}

/// A protein repository with version control.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProteinRepository {
    pub name: String,
    pub branches: HashMap<String, ProteinBranch>,
    pub versions: HashMap<String, ProteinVersion>,
    pub tags: HashMap<String, String>,
    pub current_branch: String,
}

impl ProteinRepository {
    pub fn new(name: impl Into<String>, initial_protein: Protein) -> Self {
        let name = name.into();
        let version_id = initial_protein.id.clone();

        let version = ProteinVersion {
            id: version_id.clone(),
            protein: initial_protein,
            parent_id: None,
            mutations: vec![],
            message: "Initial commit".to_string(),
            author: "system".to_string(),
            timestamp: Utc::now(),
        };

        let branch = ProteinBranch {
            name: "main".to_string(),
            head_id: version_id.clone(),
            description: "Main branch".to_string(),
        };

        let mut branches = HashMap::new();
        branches.insert("main".to_string(), branch);

        let mut versions = HashMap::new();
        versions.insert(version_id, version);

        Self {
            name,
            branches,
            versions,
            tags: HashMap::new(),
            current_branch: "main".to_string(),
        }
    }

    pub fn commit(
        &mut self,
        protein: Protein,
        mutations: Vec<Mutation>,
        message: impl Into<String>,
        author: impl Into<String>,
    ) -> String {
        let branch = self.branches.get(&self.current_branch).unwrap();
        let parent_id = branch.head_id.clone();
        let version_id = protein.id.clone();

        let version = ProteinVersion {
            id: version_id.clone(),
            protein,
            parent_id: Some(parent_id),
            mutations,
            message: message.into(),
            author: author.into(),
            timestamp: Utc::now(),
        };

        self.versions.insert(version_id.clone(), version);
        self.branches
            .get_mut(&self.current_branch)
            .unwrap()
            .head_id = version_id.clone();

        version_id
    }

    pub fn create_branch(&mut self, name: impl Into<String>, description: impl Into<String>) {
        let name = name.into();
        let head_id = self.branches[&self.current_branch].head_id.clone();
        self.branches.insert(
            name.clone(),
            ProteinBranch {
                name,
                head_id,
                description: description.into(),
            },
        );
    }

    pub fn checkout(&mut self, branch_name: &str) -> Result<(), String> {
        if self.branches.contains_key(branch_name) {
            self.current_branch = branch_name.to_string();
            Ok(())
        } else {
            Err(format!("Branch '{branch_name}' not found"))
        }
    }

    pub fn head(&self) -> &ProteinVersion {
        let branch = &self.branches[&self.current_branch];
        &self.versions[&branch.head_id]
    }

    pub fn log(&self) -> Vec<&ProteinVersion> {
        let mut history = Vec::new();
        let mut current_id = Some(self.head().id.clone());

        while let Some(id) = current_id {
            if let Some(version) = self.versions.get(&id) {
                history.push(version);
                current_id = version.parent_id.clone();
            } else {
                break;
            }
        }

        history
    }

    pub fn tag(&mut self, name: impl Into<String>) {
        let head_id = self.head().id.clone();
        self.tags.insert(name.into(), head_id);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_repository_basics() {
        let p = Protein::new("test", "MKTVRQERLK");
        let mut repo = ProteinRepository::new("test-repo", p);

        assert_eq!(repo.current_branch, "main");
        assert_eq!(repo.log().len(), 1);

        let p2 = Protein::new("test-v2", "MKTVRQERLKSIV");
        let mutations = vec![Mutation {
            position: 10,
            from: ' ',
            to: 'S',
            reason: Some("Added residues".to_string()),
        }];
        repo.commit(p2, mutations, "Extended sequence", "user");
        assert_eq!(repo.log().len(), 2);
    }

    #[test]
    fn test_branching() {
        let p = Protein::new("test", "MKTVRQERLK");
        let mut repo = ProteinRepository::new("test-repo", p);

        repo.create_branch("experiment", "Testing something");
        repo.checkout("experiment").unwrap();
        assert_eq!(repo.current_branch, "experiment");

        assert!(repo.checkout("nonexistent").is_err());
    }
}
