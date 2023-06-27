const trashSvg = (onClick) =>
  `<button type="button" class="btn btn-outline-danger" onClick="${onClick}">` +
  '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">' +
  '<path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>' +
  '<path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>' +
  "</svg>";

function deleteKeyword(sp_kw) {
  const id = `tr-${sp_kw}`;
  $(`#${id}`).remove();
}
function addKeyword() {
  const childNumber = $("#keyword-table-body").children().length;
  const sp_kw = $("#sp_keyword").val();
  console.log("Adding keyword: " + sp_kw + " at position " + childNumber);

  $(`#keyword-table-body tr:nth-child(${childNumber})`).before(
    `<tr id="tr-${sp_kw}">` +
      `<td>${sp_kw}</td>` +
      '<td class="column_action">' +
      trashSvg(`deleteKeyword('${sp_kw}')`) +
      "</td>" +
      "</tr>"
  );

  $("#sp_keyword").val("");
}
function clearKeywordTable() {
  $("#keyword-table-body")
    .children()
    .each((i, child) => {
      if (child.id != "keyword-input-row") {
        $(`#${child.id}`).remove();
      }
    });
}

function deleteSearch(idx) {
  fetch("/delete_search", {
    method: "POST",
    body: JSON.stringify({ idx: idx }),
  }).then((_res) => {
    window.location.href = "/history";
  });
}
function repeatSearch(id, by) {
  window.location.href = `/search/${by}?search_id=${id}`;
}

function showAlert(text) {
  window.alert(text);
}

function search(searchType) {
  console.log("Searching by " + searchType);
  switch (searchType) {
    case "artist":
      searchArtist();
      break;

    case "keyword":
      searchByKeyword();
      break;

    default:
      break;
  }

  return;
}
function searchArtist() {
  if (
    $("#intro-prompt").val().includes("`") ||
    $("#improver-prompt").val().includes("`") ||
    $("#prompt").val().includes("`")
  ) {
    return alert(
      "Backticks (`) are not allowed in the prompts. You can use both simple or double quotes."
    );
  }

  let search_string = $("#artist").val();
  fetch("/api/search-artist/?artist=" + search_string, {
    method: "GET",
  })
    .then((res) => res.json())
    .then((res) => {
      res.forEach((data) => {
        $("#artist-list").append(
          '<button class="btn btn-outline-secondary" style="margin:5px" onClick="searchByArtist(\'' +
            data.name.replace("'", "") +
            "','" +
            data.id +
            "')\"> " +
            data.name +
            "</button>"
        );
      });

      jQuery.noConflict();
      $("#modal_artist_select").modal("show");
    });
}
function searchByArtist(artist_name, artist_id) {
  console.log("Searching tracks by artist...");
  console.log("Artist: " + artist_name);
  let body = {
    "artist-name": artist_name,
    "artist-id": artist_id,
    ...getFormData(),
  };

  fetch("/search/artist", {
    method: "POST",
    body: JSON.stringify(body),
  }).then((_res) => {
    window.location.href = "/history";
  });
}
function searchByKeyword() {
  let sp_keywords = [];
  $("#keyword-table-body")
    .children()
    .each((i, child) => {
      if (child.id != "keyword-input-row") {
        let kws = child.id.split("-");
        sp_keywords.push(kws[1]);
      }
    });

  let body = {
    sp_keywords: sp_keywords,
    keyword: $("#keyword").val(),
    ...getFormData(),
  };

  fetch("/search/keyword", {
    method: "POST",
    body: JSON.stringify(body),
  }).then((_res) => {
    window.location.href = "/history";
  });
}

function getFormData() {
  const improving_enabled =
    $("#check-improve-song").is(":checked") ||
    $("#check-improve-intro").is(":checked");
  return {
    "limit-range-kw-txt": $("#limit-range-kw-txt").val(),
    "offset-range-txt": $("#offset-range-txt").val(),
    "check-limit-kw": $("#check-limit-kw").is(":checked") ? 1 : null,
    "check-offset": $("#check-offset").is(":checked") ? 1 : null,
    wordpress: $("#wordpress").is(":checked") ? 1 : false,
    prompt: $("#prompt").val(),
    "intro-prompt": $("#intro-prompt").val(),
    "improver-prompt": improving_enabled ? $("#improver-prompt").val() : "",
    "default-prompt": $("#default-prompt").is(":checked"),
    "default-intro-prompt": $("#default-intro-prompt").is(":checked"),
    "default-improver-prompt":
      improving_enabled && $("#default-improver-prompt").is(":checked"),
    "improve-song": $("#check-improve-song").is(":checked"),
    "improve-intro": $("#check-improve-intro").is(":checked"),
    model: $("input[name=model]:checked").val(),
  };
}

function clearHistory() {
  fetch("/clear-history", {
    method: "POST",
    body: JSON.stringify({}),
  }).then((_res) => {
    window.location.href = "/history";
  });
}

var default_prompt = $("#user-default-prompt").text();
var default_intro_prompt = $("#user-default-intro-prompt").text();
var default_improver_prompt = $("#user-default-improver-prompt").text();

$(document).ready(function () {
  $("#check-prompt").on("change", function () {
    let disable = $("#check-prompt").is(":checked");
    if (disable) {
      $("#prompt").attr("disabled", true);
      $("#prompt-rules").attr("hidden", true);
      $("#prompt").val(default_prompt);
      $("#prompt-div").attr("hidden", true);
      $("#default-prompt").attr("checked", false);
    } else {
      $("#prompt").attr("disabled", false);
      $("#prompt-rules").attr("hidden", false);
      $("#prompt-div").attr("hidden", false);
    }
  });
  $("#check-intro-prompt").on("change", function () {
    let disable = $("#check-intro-prompt").is(":checked");
    if (disable) {
      $("#intro-prompt").attr("disabled", true);
      $("#intro-prompt-rules").attr("hidden", true);
      $("#intro-prompt").val(default_intro_prompt);
      $("#intro-prompt-div").attr("hidden", true);
      $("#default-intro-prompt").attr("checked", false);
    } else {
      $("#intro-prompt").attr("disabled", false);
      $("#intro-prompt-rules").attr("hidden", false);
      $("#intro-prompt-div").attr("hidden", false);
    }
  });
  $("#check-improver-prompt").on("change", function () {
    let disable = $("#check-improver-prompt").is(":checked");
    if (disable) {
      $("#improver-prompt").attr("disabled", true);
      $("#improver-prompt-rules").attr("hidden", true);
      $("#improver-prompt").val(default_intro_prompt);
      $("#improver-prompt-div").attr("hidden", true);
      $("#default-improver-prompt").attr("checked", false);
    } else {
      $("#improver-prompt").attr("disabled", false);
      $("#improver-prompt-rules").attr("hidden", false);
      $("#improver-prompt-div").attr("hidden", false);
    }
  });

  $("#check-improve").on("change", function () {
    let disable = $("#check-improve").is(":checked");
    if (disable) {
      $("#improver-div").attr("hidden", false);
    } else {
      $("#improver-div").attr("hidden", true);
    }
  });

  $("#check-limit-kw").on("change", function () {
    let able = $("#check-limit-kw").is(":checked");
    if (able) {
      $("#limit-range-kw").attr("disabled", false);
      $("#limit-range-kw-txt").attr("disabled", false);

      $("#upper-limit").text("");
      $("#upper-limit").text(
        parseFloat($("#lower-limit").text()) +
          parseFloat($("#limit-range-kw-txt").val()) -
          1
      );
    } else {
      $("#limit-range-kw").attr("disabled", true);
      $("#limit-range-kw-txt").attr("disabled", true);

      $("#upper-limit").text("");
      $("#upper-limit").text("infinity");
    }
  });

  $("#check-offset").on("change", function () {
    let able = $("#check-offset").is(":checked");
    if (able) {
      $("#offset-range").attr("disabled", false);
      $("#offset-range-txt").attr("disabled", false);

      $("#lower-limit").text("");
      $("#lower-limit").text(parseFloat($("#offset-range-txt").val()) + 1);
      if ($("#upper-limit").text() != "infinity") {
        $("#upper-limit").text("");
        $("#upper-limit").text(
          parseFloat($("#offset-range-txt").val()) +
            parseFloat($("#limit-range-kw-txt").val())
        );
      }
    } else {
      $("#offset-range").attr("disabled", true);
      $("#offset-range-txt").attr("disabled", true);

      $("#lower-limit").text("");
      $("#lower-limit").text("1");
      if ($("#upper-limit").text() != "infinity") {
        $("#upper-limit").text("");
        $("#upper-limit").text(parseFloat($("#limit-range-kw-txt").val()));
      }
    }
  });

  $("#limit-range-kw").on("change", function () {
    let value = $("#limit-range-kw").val();
    $("#limit-range-kw-txt").val(value);

    $("#upper-limit").text("");
    if ($("#check-offset").is(":checked")) {
      $("#upper-limit").text(
        parseFloat(value) + parseFloat($("#offset-range-txt").val())
      );
    } else {
      $("#upper-limit").text(parseFloat(value));
    }
  });
  $("#limit-range-kw-txt").on("change", function () {
    let value = $("#limit-range-kw-txt").val();
    $("#limit-range-kw").val(value);

    $("#upper-limit").text("");
    if ($("#check-offset").is(":checked")) {
      $("#upper-limit").text(
        parseFloat(value) + parseFloat($("#offset-range-txt").val())
      );
    } else {
      $("#upper-limit").text(parseFloat(value));
    }
  });

  $("#offset-range").on("change", function () {
    let value = $("#offset-range").val();
    $("#offset-range-txt").val(value);

    $("#lower-limit").text("");
    $("#lower-limit").text(parseFloat(value) + 1);
    $("#upper-limit").text("");
    if ($("#check-limit-kw").is(":checked")) {
      $("#upper-limit").text(
        parseFloat(value) + parseFloat($("#limit-range-kw-txt").val())
      );
    } else {
      $("#upper-limit").text("infinity");
    }
  });
  $("#offset-range-txt").on("change", function () {
    let value = $("#offset-range-txt").val();
    $("#offset-range").val(value);

    $("#lower-limit").text("");
    $("#lower-limit").text(parseFloat(value) + 1);
    $("#upper-limit").text("");
    if ($("#check-limit-kw").is(":checked")) {
      $("#upper-limit").text(
        parseFloat(value) + parseFloat($("#limit-range-kw-txt").val())
      );
    } else {
      $("#upper-limit").text("infinity");
    }
  });
});
