// display a message
function flash(message)
{
    $("#flash").html(message).fadeIn(400);
}

function hideflash()
{
    $("#flash").fadeOut(300);
}

// ajax spinner
function spin()
{
    flash('<img src="/static/spinner.gif" />');
}

// zebra stripe result tables
function stripetables() {
    $("table.results tr").removeClass("alt");
    $("table.results tr:even").not(".abstracts").addClass("alt");

    $("table.results tr")
    .mouseover(function() {
        $(this).addClass("over");
    })
    .mouseout(function() {
        $(this).removeClass("over");
    });
}

$(document).ready(function() {
    stripetables();
    
    // fade the flash box when we move the mouse over it, hide it when it's clicked
    $("#flash")
    .click(function() {
        $(this).hide();
    })
    .mouseover(function() {
        if ($(this).is(":visible")) $(this).fadeTo(200, 0.3);
    })
    .mouseout(function() {
        if ($(this).is(":visible")) $(this).fadeTo(200, 1);
    });
    
    
});
