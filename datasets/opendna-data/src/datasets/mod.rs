//! The four datasets. Each module exposes `NAME` and `build`.

pub mod disorder;
pub mod solubility;
pub mod stability;
pub mod structures;

use anyhow::{bail, Result};

use crate::context::BuildContext;
use crate::sources::Source;

pub const ALL: [&str; 4] = [structures::NAME, stability::NAME, solubility::NAME, disorder::NAME];

pub fn build(name: &str, ctx: &mut BuildContext) -> Result<()> {
    match name {
        structures::NAME => structures::build(ctx),
        stability::NAME => stability::build(ctx),
        solubility::NAME => solubility::build(ctx),
        disorder::NAME => disorder::build(ctx),
        other => bail!("unknown dataset {other:?}; expected one of {ALL:?}"),
    }
}

/// Upstream sources needed by a dataset.
pub fn sources_for(name: &str) -> Result<&'static [Source]> {
    Ok(match name {
        structures::NAME => structures::SOURCES,
        stability::NAME => stability::SOURCES,
        solubility::NAME => solubility::SOURCES,
        disorder::NAME => disorder::SOURCES,
        other => bail!("unknown dataset {other:?}; expected one of {ALL:?}"),
    })
}
