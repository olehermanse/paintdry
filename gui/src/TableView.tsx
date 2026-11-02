import { useState, useEffect } from "react";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import type {} from "@mui/x-data-grid/themeAugmentation";
import { Box, Stack, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useNavigate } from "react-router-dom";

function columns(fields: string[]) {
  const c = [];
  for (const field of fields) {
    const o: GridColDef = {
      field: field,
      headerName: field,
      flex: 1, // fixes the issue :upside_down_face: grow to fill space
    };
    if (field === "module") {
      o.maxWidth = 100;
      o.flex = 0; // stick to 100, do not grow
    }
    if (["value", "old_value", "new_value"].includes(field)) {
      // Values can be huge (e.g. commit_signatures), don't let autosize
      // stretch the column, they're cut off (...) and the whole value is
      // shown when clicking the row:
      o.maxWidth = 400;
      // Show objects as JSON instead of [object Object]:
      o.valueFormatter = (value) =>
        typeof value === "object" ? JSON.stringify(value) : value;
    }
    c.push(o);
  }
  return c;
}

// Start of today / this week (Monday) / this month, null for all time:
function periodStart(period: string): Date | null {
  if (!period) {
    return null;
  }
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  if (period === "week") {
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
  } else if (period === "month") {
    start.setDate(1);
  }
  return start;
}

const autosizeOptions = {
  includeHeaders: true,
  includeOutliers: true,
  outliersFactor: 1.5,
  expand: true,
};

async function fetch_table_data(url: string) {
  const response = await fetch(url);
  const observations = await response.json();
  return observations;
}

function TableView({
  fields,
  api,
  dateField,
}: {
  fields: string[];
  api: string;
  // Show the today / this week / this month filter for this field:
  dateField?: string;
}) {
  const [status, setStatus] = useState("loading");
  const [rows, setRows] = useState<{ id: string; [key: string]: string }[]>([]);
  const [period, setPeriod] = useState("");
  useEffect(() => {
    fetch_table_data(api).then((data) => {
      setRows(data);
      if (data.size === 0) {
        setStatus("empty");
      } else {
        setStatus("loaded");
      }
    });
  }, [api]);

  const navigate = useNavigate();

  if (status === "loading") {
    return (
      <>
        <span>Loading...</span>
      </>
    );
  }

  if (status === "empty") {
    return (
      <>
        <span>No data.</span>
      </>
    );
  }

  const start = periodStart(period);
  const shown =
    dateField && start
      ? rows.filter((row) => new Date(row[dateField]) >= start)
      : rows;
  return (
    <Box sx={{ width: "100%" }}>
      {dateField && (
        <Stack direction="row" sx={{ my: 1 }}>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={period}
            // null when clicking the selected button, show all:
            onChange={(_event, value) => setPeriod(value ?? "")}
          >
            <ToggleButton value="">All</ToggleButton>
            <ToggleButton value="today">Today</ToggleButton>
            <ToggleButton value="week">This week</ToggleButton>
            <ToggleButton value="month">This month</ToggleButton>
          </ToggleButtonGroup>
        </Stack>
      )}
      <div style={{ height: "70vh", width: "100%" }}>
        <DataGrid
          onRowClick={(params) => {
            navigate("./" + params.id, { relative: "path" });
          }}
          disableRowSelectionOnClick={true}
          autoPageSize={true}
          autosizeOnMount={true}
          rows={shown}
          columns={columns(fields)}
          autosizeOptions={autosizeOptions}
        />
      </div>
    </Box>
  );
}

export default TableView;
