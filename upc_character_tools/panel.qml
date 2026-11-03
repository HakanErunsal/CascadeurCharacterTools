import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts

Window {
    id: window
    width: 440; height: 700
    minimumWidth: 380; minimumHeight: 360
    title: "Manny Character Tools"
    color: "#151515"
    visible: true
    flags: Qt.Window | Qt.WindowStaysOnTopHint
    onClosing: function(close) { close.accepted=false; window.visible=false }

    // Details panel building blocks

    component Section: Column {
        id: section
        property string title
        property bool expanded: true
        default property alias content: body.data
        width: parent ? parent.width : 0
        Rectangle {
            width: parent.width; height: 28
            color: headerArea.containsMouse ? "#383838" : "#2f2f2f"
            Text {
                id: arrow
                x: 8; anchors.verticalCenter: parent.verticalCenter
                text: "▾"; color: "#c0c0c0"; font.pixelSize: 12
                rotation: section.expanded ? 0 : -90
            }
            Text {
                x: 24; anchors.verticalCenter: parent.verticalCenter
                text: section.title; color: "#e6e6e6"; font.pixelSize: 12; font.bold: true
            }
            MouseArea {
                id: headerArea
                anchors.fill: parent; hoverEnabled: true
                onClicked: section.expanded = !section.expanded
            }
        }
        Column {
            id: body
            width: parent.width
            visible: section.expanded
        }
    }

    component PropertyRow: Rectangle {
        id: row
        property string label
        property string tip
        property int rowHeight: 32
        default property alias value: slot.data
        width: parent ? parent.width : 0
        height: rowHeight
        color: hover.hovered ? "#2c2c2c" : "#242424"
        HoverHandler { id: hover }
        Text {
            x: 22; width: row.width*0.38 - 28
            anchors.verticalCenter: parent.verticalCenter
            text: row.label; color: "#c0c0c0"; font.pixelSize: 12
            elide: Text.ElideRight
        }
        Rectangle { x: row.width*0.38; width: 1; height: parent.height; color: "#1a1a1a" }
        Item {
            id: slot
            x: row.width*0.38 + 8; width: row.width - x - 10
            anchors.top: parent.top; anchors.bottom: parent.bottom
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#1a1a1a" }
        ToolTip {
            visible: hover.hovered && row.tip.length > 0
            delay: 500
            text: row.tip
            contentItem: Text { text: row.tip; color: "#d0d0d0"; font.pixelSize: 11; wrapMode: Text.WordWrap }
            background: Rectangle { color: "#0f0f0f"; border.color: "#4a4a4a"; radius: 2 }
            width: Math.min(320, implicitWidth)
        }
    }

    component Field: TextField {
        id: field
        property color axis: "transparent"
        implicitHeight: 24
        leftPadding: axis.a > 0 ? 10 : 6
        rightPadding: 6; topPadding: 0; bottomPadding: 0
        verticalAlignment: TextInput.AlignVCenter
        color: "#d0d0d0"; placeholderTextColor: "#5f5f5f"
        selectionColor: "#1f6fd1"; selectedTextColor: "#ffffff"
        font.pixelSize: 12
        selectByMouse: true
        enabled: !toolModel.busy
        background: Rectangle {
            color: "#0f0f0f"; radius: 3
            border.color: field.activeFocus ? "#1f6fd1" : (field.hovered ? "#575757" : "#383838")
            Rectangle {
                visible: field.axis.a > 0
                x: 1; y: 1; width: 3; height: parent.height - 2; radius: 1
                color: field.axis
            }
        }
    }

    component UButton: Button {
        id: control
        property bool primary: false
        implicitHeight: 26
        enabled: !toolModel.busy
        font.pixelSize: 12
        contentItem: Text {
            text: control.text; font: control.font
            color: control.enabled ? "#f0f0f0" : "#7a7a7a"
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 3
            color: !control.enabled ? "#2a2a2a"
                 : control.primary ? (control.down ? "#1858a8" : control.hovered ? "#3a85e0" : "#1f6fd1")
                 : (control.down ? "#2a2a2a" : control.hovered ? "#575757" : "#383838")
        }
    }

    // Window chrome

    Rectangle {
        id: titleBar
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        height: 30
        color: "#0f0f0f"
        Text {
            anchors.left: parent.left; anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "Manny Character Tools"
            color: "#e6e6e6"; font.pixelSize: 13; font.bold: true
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onPressed: window.startSystemMove()
        }
        Rectangle {
            anchors.right: parent.right; anchors.top: parent.top
            width: 34; height: 30
            color: closeArea.containsMouse ? "#c42b1c" : "transparent"
            Text { anchors.centerIn: parent; text: "×"; color: "#e6e6e6"; font.pixelSize: 16 }
            MouseArea { id: closeArea; anchors.fill: parent; hoverEnabled: true; onClicked: window.visible = false }
        }
    }

    Flickable {
        id: scroller
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: titleBar.bottom; anchors.bottom: statusBar.top
        anchors.margins: 6
        contentHeight: sections.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {
            policy: scroller.contentHeight > scroller.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
            contentItem: Rectangle { implicitWidth: 6; radius: 3; color: "#575757" }
        }

        Column {
            id: sections
            width: scroller.width
            spacing: 2

            Section {
                title: "Add Character"
                PropertyRow {
                    label: "Name"
                    tip: "Unique name for the new character, e.g. Enemy_02. Starts with a letter; letters, numbers, spaces, _ and - allowed. Every object of the character gets this name as a prefix."
                    Field {
                        id: nameInput
                        width: parent.width; anchors.verticalCenter: parent.verticalCenter
                        placeholderText: "Enemy_02"
                        onAccepted: toolModel.addCharacter(text, offsetX.text, offsetY.text, offsetZ.text, yaw.text, characterScale.text)
                    }
                }
                PropertyRow {
                    label: "Location"
                    tip: "Starting position in Unreal centimetres (X forward, Y right, Z up). Unaffected by Scale."
                    RowLayout {
                        width: parent.width; anchors.verticalCenter: parent.verticalCenter
                        spacing: 4
                        Field { id: offsetX; Layout.fillWidth: true; text: "0"; axis: "#c83c3c" }
                        Field { id: offsetY; Layout.fillWidth: true; text: "0"; axis: "#4fa83c" }
                        Field { id: offsetZ; Layout.fillWidth: true; text: "0"; axis: "#3c6fc8" }
                    }
                }
                PropertyRow {
                    label: "Rotation (Yaw)"
                    tip: "Starting facing angle in degrees, Unreal convention. 180 turns the character around to face the first one."
                    Field { id: yaw; width: (parent.width - 8)/3; anchors.verticalCenter: parent.verticalCenter; text: "0"; axis: "#3c6fc8" }
                }
                PropertyRow {
                    label: "Scale"
                    tip: "Uniform size of the new character. 1 is standard Manny, 1.5 is half again as tall. Use for bosses or small enemies; Export Selected can write it back at standard size."
                    Field { id: characterScale; width: (parent.width - 8)/3; anchors.verticalCenter: parent.verticalCenter; text: "1" }
                }
                PropertyRow {
                    rowHeight: 38
                    UButton {
                        text: "Add Character"; primary: true
                        width: parent.width; anchors.verticalCenter: parent.verticalCenter
                        onClicked: toolModel.addCharacter(nameInput.text, offsetX.text, offsetY.text, offsetZ.text, yaw.text, characterScale.text)
                    }
                }
            }

            Section {
                title: "Export"
                PropertyRow {
                    label: "Selection"
                    tip: "The character and Timeline interval that Export Selected uses. Select any joint, mesh, point or AutoPosing control of one character, then select frames in the Timeline."
                    rowHeight: Math.max(32, selectionText.implicitHeight + 14)
                    Text {
                        id: selectionText
                        width: parent.width; anchors.verticalCenter: parent.verticalCenter
                        text: toolModel.selection; color: "#e6e6e6"; font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }
                PropertyRow {
                    label: "Root Motion"
                    tip: "Body Facing takes the root's turn from the pelvis direction; use it for paired animations where the character was placed or turned. Root Heading keeps the turn already keyed on the root joint."
                    ComboBox {
                        id: heading
                        width: parent.width; implicitHeight: 24; anchors.verticalCenter: parent.verticalCenter
                        enabled: !toolModel.busy
                        font.pixelSize: 12
                        model: ["Body Facing", "Root Heading"]
                        contentItem: Text {
                            leftPadding: 8; text: heading.displayText; font: heading.font
                            color: "#d0d0d0"; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
                        }
                        indicator: Text {
                            x: heading.width - width - 8; anchors.verticalCenter: parent.verticalCenter
                            text: "▾"; color: "#c0c0c0"; font.pixelSize: 12
                        }
                        background: Rectangle {
                            radius: 3; color: heading.hovered ? "#2a2a2a" : "#0f0f0f"
                            border.color: heading.popup.visible ? "#1f6fd1" : "#383838"
                        }
                        delegate: ItemDelegate {
                            width: heading.width; height: 24
                            highlighted: heading.highlightedIndex === index
                            contentItem: Text { text: modelData; color: "#d0d0d0"; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter }
                            background: Rectangle { color: highlighted ? "#1f6fd1" : "#1a1a1a" }
                        }
                        popup.background: Rectangle { color: "#1a1a1a"; border.color: "#383838" }
                    }
                }
                PropertyRow {
                    label: "Frame Rate"
                    tip: "Leave empty to use the scene's Frame rate setting. Typing a value (e.g. 30) makes the export stop if the scene runs at a different rate."
                    Field { id: fps; width: (parent.width - 8)/3; anchors.verticalCenter: parent.verticalCenter; placeholderText: "Scene" }
                }
                PropertyRow {
                    label: "Standard Size"
                    tip: "On: a character added with a Scale other than 1 is exported at normal Manny size, root motion included, so it plays on the standard Unreal skeleton. Scale the actor in Unreal to get its size back. Off: the skeleton is exported at its size in the scene."
                    CheckBox {
                        id: normalizeSize
                        anchors.verticalCenter: parent.verticalCenter
                        checked: true
                        enabled: !toolModel.busy
                        padding: 0
                        text: "Export at standard Manny size"
                        indicator: Rectangle {
                            width: 16; height: 16; radius: 2
                            anchors.verticalCenter: parent.verticalCenter
                            color: normalizeSize.checked ? "#1f6fd1" : "#0f0f0f"
                            border.color: normalizeSize.hovered ? "#8a8a8a" : "#4a4a4a"
                            Text {
                                anchors.centerIn: parent; visible: normalizeSize.checked
                                text: "✓"; color: "#ffffff"; font.pixelSize: 12; font.bold: true
                            }
                        }
                        contentItem: Text {
                            leftPadding: 24; text: normalizeSize.text
                            color: "#d0d0d0"; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
                PropertyRow {
                    rowHeight: 38
                    UButton {
                        text: "Export Selected"; primary: true
                        width: parent.width; anchors.verticalCenter: parent.verticalCenter
                        onClicked: toolModel.exportSelected(heading.currentIndex, fps.text, normalizeSize.checked)
                    }
                }
                Rectangle {
                    width: parent.width; height: exportHelp.implicitHeight + 14; color: "#1f1f1f"
                    Text {
                        id: exportHelp
                        x: 22; width: parent.width - 32; anchors.verticalCenter: parent.verticalCenter
                        text: "Exports the selected Timeline interval, both ends included. The first frame is moved to the origin; motion after it is kept. The .casc file is not changed."
                        color: "#8a8a8a"; font.pixelSize: 11; wrapMode: Text.WordWrap
                    }
                }
            }

            Section {
                title: "Live Link"
                expanded: false
                PropertyRow {
                    rowHeight: 38
                    tip: "Removes the name prefix from every joint, control and mesh of the selected character so Live Link bone names match the Unreal skeleton. Reconnect the Live Link source afterwards. Undo restores the prefix."
                    UButton {
                        text: "Nativize Selected"
                        width: parent.width; anchors.verticalCenter: parent.verticalCenter
                        onClicked: toolModel.nativizeSelected()
                    }
                }
            }
        }
    }

    Rectangle {
        id: statusBar
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: Math.max(28, statusText.implicitHeight + 12)
        color: "#0f0f0f"
        Rectangle {
            id: statusDot
            x: 12; anchors.verticalCenter: parent.verticalCenter
            width: 8; height: 8; radius: 4
            color: toolModel.busy ? "#e0a030" : "#3fae5f"
        }
        Text {
            id: statusText
            x: 28; width: parent.width - 40; anchors.verticalCenter: parent.verticalCenter
            text: toolModel.status; color: "#c0c0c0"; font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
    }
}
