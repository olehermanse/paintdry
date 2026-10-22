import { useState, useEffect } from "react";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import {
  Button,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import { useNavigate } from "react-router-dom";

interface Sbom {
  id: string;
  org: string;
  repo: string;
  type: string;
  name: string;
  scanned: string;
}

const columns: GridColDef[] = [
  { field: "org", headerName: "org", flex: 1 },
  { field: "repo", headerName: "repo", flex: 1 },
  { field: "type", headerName: "type", maxWidth: 100, flex: 0 },
  { field: "name", headerName: "branch / tag", flex: 1 },
  {
    field: "scanned",
    headerName: "last scanned",
    flex: 1,
    valueFormatter: (value: string) => new Date(value).toLocaleString(),
  },
  {
    field: "download",
    headerName: "",
    sortable: false,
    renderCell: (params) => (
      <Button
        variant="outlined"
        size="small"
        href={`/api/sboms/${params.id}`}
        // Download only, don't also open the row:
        onClick={(event) => event.stopPropagation()}
      >
        Download
      </Button>
    ),
  },
];

function unique(values: string[]) {
  return [...new Set(values)];
}

function SbomView() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Sbom[] | null>(null);
  const [search, setSearch] = useState("");
  const [org, setOrg] = useState("");
  const [repo, setRepo] = useState("");
  const [type, setType] = useState("");
  useEffect(() => {
    fetch("/api/sboms")
      .then((response) => response.json())
      .then(setRows);
  }, []);

  if (rows === null) {
    return <span>Loading...</span>;
  }
  if (rows.length === 0) {
    return <span>No data.</span>;
  }
  const repos = unique(
    rows.filter((r) => !org || r.org === org).map((r) => r.repo),
  );
  const shown = rows.filter(
    (r) =>
      (!org || r.org === org) &&
      (!repo || r.repo === repo) &&
      (!type || r.type === type) &&
      `${r.org}/${r.repo} ${r.name}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ my: 1 }}>
        <TextField
          label="Search"
          size="small"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <TextField
          select
          label="Org"
          size="small"
          sx={{ minWidth: 160 }}
          value={org}
          onChange={(event) => {
            setOrg(event.target.value);
            setRepo("");
          }}
        >
          <MenuItem value="">All</MenuItem>
          {unique(rows.map((r) => r.org)).map((o) => (
            <MenuItem key={o} value={o}>
              {o}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Repo"
          size="small"
          sx={{ minWidth: 200 }}
          value={repo}
          onChange={(event) => setRepo(event.target.value)}
        >
          <MenuItem value="">All</MenuItem>
          {repos.map((r) => (
            <MenuItem key={r} value={r}>
              {r}
            </MenuItem>
          ))}
        </TextField>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={type}
          // null when clicking the selected button, show all:
          onChange={(_event, value) => setType(value ?? "")}
        >
          <ToggleButton value="">All</ToggleButton>
          <ToggleButton value="branch">Branches</ToggleButton>
          <ToggleButton value="tag">Tags</ToggleButton>
        </ToggleButtonGroup>
        <form method="post" action="/api/sboms/archive">
          <input
            type="hidden"
            name="ids"
            value={JSON.stringify(shown.map((r) => r.id))}
          />
          <Button type="submit" variant="contained" disabled={!shown.length}>
            Download {shown.length} (.tar.gz)
          </Button>
        </form>
      </Stack>
      <div style={{ height: "70vh", width: "100%" }}>
        <DataGrid
          rows={shown}
          columns={columns}
          autoPageSize={true}
          disableColumnMenu={true}
          disableRowSelectionOnClick={true}
          // The id contains slashes, e.g. cfengine/cfbs/tags/3.27.0:
          onRowClick={(params) =>
            navigate("./" + encodeURIComponent(params.id), { relative: "path" })
          }
        />
      </div>
    </>
  );
}

export default SbomView;
