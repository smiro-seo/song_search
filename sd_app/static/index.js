function delete_row(idx, table) {
  if (table == "input") {
    fetch("/delete_row", {
      method: "POST",
      body: JSON.stringify({ idx: idx }),
    }).then((_res) => {
      window.location.href = "/search";
    });
  } else if (table == "history") {
    fetch("/delete_search", {
      method: "POST",
      body: JSON.stringify({ idx: idx }),
    }).then((_res) => {
      window.location.href = "/history";
    });
  }
}

function repeat_search(keyword_json) {
  fetch("/repeat_search", {
    method: "POST",
    body: JSON.stringify({ keyword: keyword_json }),
  }).then((_res) => {
    window.location.href = "/search";
  });
}

function search_artist() {
  let search_string = $("#artist").val();
  fetch("/api/search-artist/?artist=" + search_string, {
    method: "GET",
  })
    .then((res) => res.json())
    .then((res) => {
      res.forEach((data) => {
        $("#artist-list").append(
          '<button class="btn btn-outline-secondary" style="margin:5px" onClick="search_by_artist(\'' +
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
function search_by_artist(artist_name, artist_id) {
  console.log("hasta aca bien: " + artist_name);
  let body = {
    "artist-name": artist_name,
    "artist-id": artist_id,
    "limit-range-kw-txt": $("#limit-range-kw-txt").val(),
    "offset-range-txt": $("#offset-range-txt").val(),
    "check-limit-kw": $("#check-limit-kw").is(":checked") ? 1 : null,
    "check-offset": $("#check-offset").is(":checked") ? 1 : null,
    wordpress: $("#wordpress").is(":checked") ? 1 : false,
  };
  console.log(body);

  fetch("/search-by-artist", {
    method: "POST",
    body: JSON.stringify(body),
  }).then((_res) => {
    window.location.href = "/history";
  });
}

function clear_table(what_to_clear) {
  fetch("/clear", {
    method: "POST",
    body: JSON.stringify({ what_to_clear: what_to_clear }),
  }).then((_res) => {
    window.location.href = "/search";
  });
}

$(document).ready(function () {
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
