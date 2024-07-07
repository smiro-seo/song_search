const trashSvg = (onClick) =>
  `<button type="button" class="btn btn-outline-danger" onClick="${onClick}">` +
  '<i class="bi bi-trash-fill"></i></button>';

let imgSrc = document.body.getAttribute("data-img-src");
let default_prompt = $("#user-default-prompt").text();
let default_intro_prompt = $("#user-default-intro-prompt").text();
let default_improver_prompt = $("#user-default-improver-prompt").text();
let default_img_prompt = $("#user-default-img-prompt").text();

function copyTextToClipboard(text, ident) {
  if (!navigator.clipboard) {
    return;
  }
  navigator.clipboard.writeText(text).then(
    function () {
      console.log("Async: Copying to clipboard was successful!");
      ident.tooltip("show");
      setTimeout(() => ident.tooltip("hide"), 1000);
    },
    function (err) {
      console.error("Async: Could not copy text: ", err);
    }
  );
}
function setAr(ar) {
  $("#img-config-ar").val(ar);
  $("#img-config-ar-btn").text(ar);
}

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

function clearImgKeywords(where) {
  $(`[id^='${where}-img-kw-']`).remove();
  return;
}
function addImgKeyword(where) {
  const kw = $(`#${where}-img-keyword`).val();
  const kwId = where + "-img-kw-" + kw.replace(" ", "-");

  $(`#${where}-img-kws-container`).append(
    `<div class="btn-group" role="group" id="${kwId}" aria-label="keyword for image">` +
      `<button type="button" class="btn btn-secondary">${kw}</button>` +
      `<button type="button" class="btn btn-secondary" onClick="deleteImgKeyword('${kw}', '${where}')">X</button>` +
      `</div>`
  );

  $(`#${where}-img-keyword`).val("");
}
function deleteImgKeyword(kw, where) {
  const kwId = where + "-img-kw-" + kw.replace(" ", "-");
  console.log(kwId);
  $("#" + kwId).remove();
}

function deleteSearch(idx) {
  fetch("/delete_search", {
    method: "POST",
    body: JSON.stringify({ idx: idx }),
  }).then((_res) => {
    window.location.href = "/history";
  });
}

function deleteSpotifyDraft(idx, searchedby){
  console.log(searchedby)
  fetch("/deleteSpotifyDraft", {
    method: "POST",
    body: JSON.stringify({ idx: idx }),
  }).then((_res) => {
    console.log()
    if(String(searchedby) === "artist")
        {window.location.href = "/spotifyDrafts/artist";}
      else{
        window.location.href = "/spotifyDrafts/keyword";
      }
    });
}
function repeatSearch(id, by) {
  window.location.href = `/search/${by}?search_id=${id}`;
}

function proceed(by){
  let body = {
    ...getFormData(),
  };

  fetch(`/proceed/${by}`, {
    method: "GET",
    params: JSON.stringify(body),
  }).then((_res) => {
    window.location.href = `/proceed/${by}`;
  });
}

function showDetails(searchData) {
  const modal = new bootstrap.Modal(
    document.getElementById("modal-search-details"),
    {}
  );

  const properties = [
    "date",
    "user",
    "model",
    "intro-prompt",
    "improver-prompt",
    "prompt",
    "status",
    "keywords",
    "by",
    "img-prompt",
    "seed",
    "n-img-keywords",
    "p-img-keywords",
    "img-gen-prompt",
  ];

  for (let p of properties) {
    $(`#details-${p}`).text(searchData[p]);
    if (p.includes("prompt")) {
      $(`#details-${p}-copy`).attr("onclick", "");

      $(`#details-${p}-copy`).click(() =>
        copyTextToClipboard(searchData[p], $(`#details-${p}-copy`))
      );
    }
  }

  const hiddableProperties = {
    "intro-improved": searchData.improved_intro,
    "song-improved": searchData.improved_song,
    "p-img-keywords-row": searchData["p-img-keywords"].length > 0,
    "n-img-keywords-row": searchData["n-img-keywords"].length > 0,
    "improver-row": searchData.improved_song || searchData.improved_intro,
  };

  for (let k of Object.keys(hiddableProperties)) {
    if (hiddableProperties[k]) $(`#details-${k}`).attr("hidden", false);
    else $(`#details-${k}`).attr("hidden", true);
  }

  if (searchData.include_img) {
    $("#details-img-row").attr("hidden", false);

    const img_url = `${imgSrc}/${searchData.img_config?.seed}.jpeg`;
    $.get(img_url)
      .done(function () {
        $("#details-img-src").attr(
          "src",
          img_url
        );
        $("#details-img-row-src").attr("hidden", false);
      })
      .fail(function () {
        console.log("Failed search for the image");
        $("#details-img-row-src").attr("hidden", true);
      });
  } else {
    $("#details-img-row").attr("hidden", true);
  }
  modal.show();
}

function showAlert(text) {
  window.alert(text);
}

function toggleSelectAll(selectAllCheckbox) {
  var checkboxes = document.querySelectorAll('.draft-checkbox');
  checkboxes.forEach(function(checkbox) {
      checkbox.checked = selectAllCheckbox.checked;
  });
}

// document.getElementById('deleteForm').addEventListener('submit', function(event) {
//   var checkboxes = document.querySelectorAll('input[name="selected_drafts"]:checked');
//   if (checkboxes.length === 0) {
//       event.preventDefault();
//       alert('Please select at least one item to delete.');
//   }
//   console.log(checkboxes)

//   alert(checkboxes)
// });

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


function finalize(searchType) {
  console.log("Searching by " + searchType);
  let body = {
    ...getFormData(),
  };

  fetch("/proceed/" + searchType, {
    method: "POST",
    body: JSON.stringify(body),
  }).then((_res) => {
    window.location.href = "/history";
  });
}

function searchSpotify(searchType) {
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
  if ($("#artist").val() == "") {
    return alert("Please write something in the 'Artist' field");
  }

  let search_string = $("#artist").val();
  fetch("/api/search-artist/?artist=" + search_string, {
    method: "GET",
  })
    .then((res) => res.json())
    .then((res) => {
      console.log("Rendergin artist list");
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
      const modal = new bootstrap.Modal(
        document.getElementById("modal_artist_select"),
        {}
      );
      modal.show();
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

  fetch("/searchSpotify/artist", {
    method: "POST",
    body: JSON.stringify(body),
  }).then((_res) => {
    window.location.href = "/spotifyDrafts/artist";
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

  if ($("#keyword").val() == "") {
    return alert("Please write something in the 'Keyword' field");
  } else if (sp_keywords.length == 0) {
    return alert(
      "Please add at least one word in the 'Specific keyword' section"
    );
  }

  let body = {
    sp_keywords: sp_keywords,
    keyword: $("#keyword").val(),
    ...getFormData(),
  };

  fetch("/searchSpotify/keyword", {
    method: "POST",
    body: JSON.stringify(body),
  }).then((_res) => {
    window.location.href = "/spotifyDrafts/keyword";
  });
}

function getFormData() {
  let p_img_kw = [];
  let n_img_kw = [];
  $(`#p-img-kws-container`)
    .children()
    .each(function () {
      p_img_kw.push($($(this).children()[0]).text());
    });
  $(`#n-img-kws-container`)
    .children()
    .each(function () {
      n_img_kw.push($($(this).children()[0]).text());
    });

  const improving_enabled =
    $("#check-improve-song").is(":checked") ||
    $("#check-improve-intro").is(":checked");

  const img_config = {
    steps: $("#img-config-steps-txt").val(),
    "aspect-ratio": $("#img-config-ar").val(),
  };
  const def_img_config = Object.keys(img_config).filter((c) =>
    $(`#default-img-${c}`).is(":checked")
  );

  return {
    "keyword": $("#keyword").val(),
    "summary": $("#summary").val(),
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
    "default-img-prompt": $("#default-img-prompt").is(":checked"),
    "default-improver-prompt":
      improving_enabled && $("#default-improver-prompt").is(":checked"),
    "improve-song": $("#check-improve-song").is(":checked"),
    "improve-intro": $("#check-improve-intro").is(":checked"),
    model: $("input[name=model]:checked").val(),

    "include-img": $("#include-img").is(":checked"),
    "img-prompt": $("#img-prompt").val(),
    "image-prompt-keywords": p_img_kw,
    "image-nprompt-keywords": n_img_kw,

    "img-config": img_config,
    "default-img-config": def_img_config,
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

function clearySpotifyDraft(by){
  fetch("/clear-spotifyDraft", {
    method: "POST",
    body: JSON.stringify({}),
  }).then((_res) => {
    window.location.href = "/spotifyDrafts/" + by;
  });
}

function resetPrompt(prompt) {
  switch (prompt) {
    case "intro":
      $("#intro-prompt").val(default_intro_prompt);
      break;
    case "song":
      $("#prompt").val(default_prompt);
      break;
    case "improver":
      $("#improver-prompt").val(default_improver_prompt);
      break;
    case "img":
      $("#img-prompt").val(default_img_prompt);
      break;
  }
}

$(document).ready(function () {
  let tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  let tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // ACCORDION TITLE UPDATE
  $("#artist").on("change", () => {
    const newArt = $("#artist").val();
    $("#artist-accordion-title").text(`(${newArt})`);
  });
  $("#keyword").on("change", () => {
    const newArt = $("#keyword").val();
    $("#keyword-accordion-title").text(`(${newArt})`);
  });

  // IMPROVER
  const checkImprove = () => {
    console.log("Checking if is improved");
    const improving_enabled =
      $("#check-improve-song").is(":checked") ||
      $("#check-improve-intro").is(":checked");

    $("#improver-prompt-div").attr("hidden", !improving_enabled);
  };
  $("#check-improve-song").on("change", function () {
    checkImprove();
  });
  $("#check-improve-intro").on("change", function () {
    checkImprove();
  });

  // INCLUDE IMAGE
  $("#include-img").on("change", function () {
    const enabled = $("#include-img").is(":checked");

    $("#acc-btn-img").attr("disabled", !enabled);
    if (!enabled) {
      $("#img-acc-item").collapse("hide");
      $("#acc-btn-img").addClass("collapsed");
    }
  });
  $("#acc-btn-img").on("click", function () {
    const enabled = $("#include-img").is(":checked");

    if (enabled) {
      if ($("#img-acc-item").hasClass("show")) {
        $("#img-acc-item").collapse("hide");
        $("#acc-btn-img").addClass("collapsed");
      } else {
        $("#img-acc-item").collapse("show");
        $("#acc-btn-img").removeClass("collapsed");
      }
    }
  });
  $(".accordion-button").on("click", function (e) {
    if (
      !$("#acc-btn-img").hasClass("collapsed") &&
      e.currentTarget.id != "acc-btn-img"
    ) {
      $("#acc-btn-img").addClass("collapsed");
    }
  });

  //  OFFSET / LIMIT
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

  //  IMG CONFIG
  $("#img-config-steps").on("change", function () {
    let value = $("#img-config-steps").val();
    $("#img-config-steps-txt").val(value);
  });
  $("#img-config-steps-txt").on("change", function () {
    let value = $("#img-config-steps-txt").val();
    if (value > 150) {
      $("#img-config-steps").val(150);
      $("#img-config-steps-txt").val(150);
    } else if (value < 10) {
      $("#img-config-steps").val(10);
      $("#img-config-steps-txt").val(10);
    } else {
      $("#img-config-steps").val(Math.round(value));
      $("#img-config-steps-txt").val(Math.round(value));
    }
  });
});


function toggleInputFields() {
  var searchByTrackId = document.getElementById('searchByTrackId').checked;
  document.getElementById('trackIdGroup').style.display = searchByTrackId ? 'block' : 'none';
  document.getElementById('artistNameGroup').style.display = searchByTrackId ? 'none' : 'block';
  document.getElementById('trackNameGroup').style.display = searchByTrackId ? 'none' : 'block';
}