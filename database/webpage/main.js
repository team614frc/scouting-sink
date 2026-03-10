const DISPLAY_SCHEMA = {
  titleField: "team_id",
  sections: [
    {
      title: "General",
      fields: [
        { key: "team_id", label: "Team ID" },
        { key: "notes", label: "Notes" },
        { key: "priority", label: "Priority" },
        { key: "approved", label: "Approved" }
      ]
    },
    {
      title: "Match Notes",
      field: "match_notes",
      type: "list"
    }
  ]
}

function renderDatabase(data) {
    const container = document.getElementById("records-container")
    container.innerHTML = ""

    const records = Array.isArray(data.records) ? data.records : []

    if (records.length === 0) {
        container.innerHTML = "<p>No records found.</p>"
        return
    }

    records.forEach((record, index) => {
        container.appendChild(createRecordCard(record, index))
    })
}

function createRecordCard(record, index) {
    const card = document.createElement("div")
    card.className = "record-card"

    const title = document.createElement("h3")
    title.textContent = record.team_id || `Record ${index + 1}`
    card.appendChild(title)

    const fields = [
        ["Team ID", record.team_id],
        ["Notes", record.notes],
        ["Priority", record.priority],
        ["Approved", record.approved]
    ]

    fields.forEach(([label, value]) => {
        const row = document.createElement("div")
        row.className = "record-row"

        const labelEl = document.createElement("strong")
        labelEl.textContent = `${label}: `

        const valueEl = document.createElement("span")
        valueEl.textContent = formatValue(value)

        row.appendChild(labelEl)
        row.appendChild(valueEl)
        card.appendChild(row)
    })

    if (Array.isArray(record.match_notes)) {
        const section = document.createElement("div")
        section.className = "record-section"

        const sectionTitle = document.createElement("h4")
        sectionTitle.textContent = "Match Notes"
        section.appendChild(sectionTitle)

        record.match_notes.forEach(item => {
            const itemBox = document.createElement("div")
            itemBox.className = "sub-card"
            itemBox.textContent = `${item.match}: ${item.notes}`
            section.appendChild(itemBox)
        })

        card.appendChild(section)
    }

    return card
}

function formatValue(value) {
    if (value === true) return "Yes"
    if (value === false) return "No"
    if (value == null) return ""
    if (typeof value === "object") return JSON.stringify(value)
    return String(value)
}

async function fetchJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(await r.text());
  return await r.json();
}

async function loadDb() {
    const response = await fetch("/api/database")
    const data = await response.json()
    console.log(data)
    renderDatabase(data)
}

// document.getElementById("refreshBtn").addEventListener("click", loadDb);

loadDb();
setInterval(loadDb, 500);