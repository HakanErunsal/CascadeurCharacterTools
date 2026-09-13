import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: window
    width: 460; height: 560
    minimumWidth: 410; minimumHeight: 540
    title: "Manny Character Tools"
    color: "#25282e"
    visible: true
    flags: Qt.Window | Qt.WindowStaysOnTopHint
    onClosing: function(close) { close.accepted=false; window.visible=false }

    Rectangle {
        id: titleBar
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        height: 30
        color: "#1d2025"
        Label {
            anchors.left: parent.left; anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "Manny Character Tools"
            color: "#f1f3f5"; font.pixelSize: 15; font.bold: true
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onPressed: window.startSystemMove()
        }
        Button {
            anchors.right: parent.right; anchors.top: parent.top
            width: 34; height: 30; z: 1
            text: "×"; flat: true
            onClicked: window.visible = false
            ToolTip.visible: hovered
            ToolTip.text: "Close"
        }
    }

    ColumnLayout {
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: titleBar.bottom; anchors.bottom: parent.bottom
        anchors.leftMargin: 22; anchors.rightMargin: 22
        anchors.topMargin: 16; anchors.bottomMargin: 22
        spacing: 14
        TextField {
            id: nameInput
            Layout.fillWidth: true
            placeholderText: "Character name, e.g. Enemy_02"
            selectByMouse: true
            enabled: !toolModel.busy
            onAccepted: toolModel.addCharacter(text, offsetX.text, offsetY.text, offsetZ.text, yaw.text)
        }
        Label { text: "Initial transform (Unreal cm / degrees)"; color: "#aeb8c7"; font.pixelSize: 12 }
        GridLayout {
            Layout.fillWidth: true; columns: 4; columnSpacing: 8; rowSpacing: 4
            Label { text: "X"; color: "#e0e4eb" }
            Label { text: "Y"; color: "#e0e4eb" }
            Label { text: "Z"; color: "#e0e4eb" }
            Label { text: "Yaw°"; color: "#e0e4eb" }
            TextField { id: offsetX; Layout.fillWidth: true; text: "0"; selectByMouse: true; enabled: !toolModel.busy }
            TextField { id: offsetY; Layout.fillWidth: true; text: "0"; selectByMouse: true; enabled: !toolModel.busy }
            TextField { id: offsetZ; Layout.fillWidth: true; text: "0"; selectByMouse: true; enabled: !toolModel.busy }
            TextField { id: yaw; Layout.fillWidth: true; text: "0"; selectByMouse: true; enabled: !toolModel.busy }
        }
        Button {
            text: "Add Character"; Layout.fillWidth: true
            enabled: !toolModel.busy
            onClicked: toolModel.addCharacter(nameInput.text, offsetX.text, offsetY.text, offsetZ.text, yaw.text)
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#515761" }
        Label { text: toolModel.selection; color: "#e0e4eb"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        ComboBox {
            id: heading
            Layout.fillWidth: true
            model: ["Body facing → root motion", "Use existing root heading"]
            enabled: !toolModel.busy
            ToolTip.visible: hovered
            ToolTip.text: "Body facing extracts root yaw from the pelvis while preserving the pose. Existing root heading keeps your authored root rotations."
        }
        Button {
            text: "Export Selected"; Layout.fillWidth: true
            enabled: !toolModel.busy
            onClicked: toolModel.exportSelected(heading.currentIndex)
        }
        Label {
            text: "Starts at origin. Preserves motion after the start frame.\nExports your selected interval, including both ends."
            color: "#aeb8c7"; wrapMode: Text.WordWrap
            Layout.fillWidth: true; font.pixelSize: 12
        }
        Item { Layout.fillHeight: true }
        Label { text: toolModel.status; color: "#91d4bd"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
