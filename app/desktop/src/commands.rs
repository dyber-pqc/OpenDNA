//! Tauri command handlers. Each is a thin adapter: validate input, call into
//! the library crates, convert the result to a protocol type.

use crate::{import, reports, state::AppState};
use opendna_app_protocol::{
    CommandError, ProteinDetail, ProteinSummary, SequenceReport, StructurePayload, StructureReport,
};
use std::fmt::Display;
use std::path::PathBuf;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

type CommandResult<T> = Result<T, CommandError>;

pub(crate) fn fail(e: impl Display) -> CommandError {
    CommandError { message: e.to_string() }
}

fn summary(
    db: &opendna_store::Database,
    stored: &opendna_store::StoredProtein,
) -> CommandResult<ProteinSummary> {
    Ok(ProteinSummary {
        id: stored.id.clone(),
        name: stored.protein.name.clone(),
        length: stored.protein.sequence.len(),
        has_structure: db.structure(&stored.id).map_err(fail)?.is_some(),
    })
}

#[tauri::command]
pub fn list_proteins(state: State<'_, AppState>) -> CommandResult<Vec<ProteinSummary>> {
    let db = state.db();
    db.list().map_err(fail)?.iter().map(|p| summary(&db, p)).collect()
}

/// Import a file. With no `path`, shows a native open dialog; cancelling
/// returns an empty list. Runs off the main thread so the dialog can block.
#[tauri::command(async)]
pub fn import_file(
    app: AppHandle,
    state: State<'_, AppState>,
    path: Option<String>,
) -> CommandResult<Vec<ProteinSummary>> {
    let path = if let Some(p) = path {
        PathBuf::from(p)
    } else {
        let picked = app
            .dialog()
            .file()
            .set_title("Import structure or sequence")
            .add_filter("Structures and sequences", import::EXTENSIONS)
            .blocking_pick_file();
        match picked {
            Some(file) => file.into_path().map_err(fail)?,
            None => return Ok(Vec::new()),
        }
    };
    let db = state.db();
    let ids = import::import_path(&db, &path)?;
    ids.iter()
        .map(|id| {
            let stored = db.get(id).map_err(fail)?.ok_or_else(|| fail("imported protein vanished"))?;
            summary(&db, &stored)
        })
        .collect()
}

#[tauri::command]
pub fn get_protein(state: State<'_, AppState>, id: String) -> CommandResult<ProteinDetail> {
    let db = state.db();
    let stored = db.get(&id).map_err(fail)?.ok_or_else(|| fail(format!("no protein with id {id}")))?;
    let structure = db.structure(&id).map_err(fail)?.map(|f| StructurePayload {
        format: f.format.as_str().to_string(),
        chain: f.chain,
        content: f.content,
    });
    Ok(ProteinDetail {
        summary: summary(&db, &stored)?,
        sequence: stored.protein.sequence.to_string(),
        structure,
    })
}

#[tauri::command]
pub fn delete_protein(state: State<'_, AppState>, id: String) -> CommandResult<()> {
    state.db().delete(&id).map_err(fail).map(|_| ())
}

#[tauri::command]
pub fn analyze_sequence(state: State<'_, AppState>, id: String) -> CommandResult<SequenceReport> {
    let stored =
        state.db().get(&id).map_err(fail)?.ok_or_else(|| fail(format!("no protein with id {id}")))?;
    reports::sequence(&stored.protein.sequence)
}

#[tauri::command(async)]
pub fn analyze_structure(state: State<'_, AppState>, id: String) -> CommandResult<StructureReport> {
    let file =
        state.db().structure(&id).map_err(fail)?.ok_or_else(|| fail("this protein has no structure"))?;
    reports::structure(&file)
}
