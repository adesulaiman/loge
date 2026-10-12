"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { Form, Formik } from "formik";
import * as Yup from "yup";
import { IconLoader } from "@opal/loaders";
import { BasicModalFooter, Button, Modal } from "@opal/components";
import { SvgUserPlus } from "@opal/icons";
import { InputVertical, toast } from "@opal/layouts";
import { mutate } from "swr";
import { SWR_KEYS } from "@/lib/swr-keys";
import InputTypeInField from "@/refresh-components/form/InputTypeInField";
import PasswordInputTypeInField from "@/refresh-components/form/PasswordInputTypeInField";
import { createUser } from "./svc";

interface CreateUserModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface CreateUserFormValues {
  email: string;
  password: string;
  confirmPassword: string;
}

export default function CreateUserModal({
  open,
  onOpenChange,
}: CreateUserModalProps) {
  const t = useTranslations("admin.users");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleClose = useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  const handleOpenChange = useCallback(
    (next: boolean) => {
      if (!next) {
        if (!isSubmitting) handleClose();
      } else {
        onOpenChange(next);
      }
    },
    [handleClose, isSubmitting, onOpenChange]
  );

  const validationSchema = Yup.object().shape({
    email: Yup.string()
      .trim()
      .email(t("createModal.email.invalid"))
      .required(t("createModal.email.required")),
    password: Yup.string()
      .min(8, t("createModal.password.minLength"))
      .required(t("createModal.password.required")),
    confirmPassword: Yup.string()
      .oneOf([Yup.ref("password")], t("createModal.confirmPassword.mismatch"))
      .required(t("createModal.confirmPassword.required")),
  });

  return (
    <Modal open={open} onOpenChange={handleOpenChange}>
      <Modal.Content width="sm" height="fit">
        <Modal.Header
          icon={SvgUserPlus}
          title={t("createModal.title")}
          description={t("createModal.description")}
          onClose={isSubmitting ? undefined : handleClose}
        />

        <Formik<CreateUserFormValues>
          initialValues={{ email: "", password: "", confirmPassword: "" }}
          validationSchema={validationSchema}
          enableReinitialize
          onSubmit={async (values, helpers) => {
            setIsSubmitting(true);
            try {
              await createUser({
                email: values.email.trim().toLowerCase(),
                password: values.password,
              });
              void Promise.all([
                mutate(SWR_KEYS.acceptedUsers),
                mutate(SWR_KEYS.invitedUsers),
                mutate(SWR_KEYS.userCounts),
              ]).catch(() => {});
              toast.success(t("createModal.toasts.created"));
              helpers.resetForm();
              handleClose();
            } catch (err) {
              toast.error(
                err instanceof Error
                  ? err.message
                  : t("createModal.toasts.createFailed")
              );
            } finally {
              setIsSubmitting(false);
              helpers.setSubmitting(false);
            }
          }}
        >
          {({ isValid, dirty, submitForm }) => (
            <Form>
              <Modal.Body alignItems="stretch" gap={1}>
                <InputVertical
                  title={t("createModal.email.label")}
                  withLabel="email"
                >
                  <InputTypeInField
                    name="email"
                    type="email"
                    placeholder={t("createModal.email.placeholder")}
                    autoComplete="off"
                  />
                </InputVertical>
                <InputVertical
                  title={t("createModal.password.label")}
                  withLabel="password"
                >
                  <PasswordInputTypeInField
                    name="password"
                    placeholder={t("createModal.password.placeholder")}
                    autoComplete="new-password"
                  />
                </InputVertical>
                <InputVertical
                  title={t("createModal.confirmPassword.label")}
                  withLabel="confirmPassword"
                >
                  <PasswordInputTypeInField
                    name="confirmPassword"
                    placeholder={t("createModal.confirmPassword.placeholder")}
                    autoComplete="new-password"
                  />
                </InputVertical>
              </Modal.Body>

              <Modal.Footer>
                <BasicModalFooter
                  cancel={
                    <Button
                      disabled={isSubmitting}
                      prominence="tertiary"
                      onClick={handleClose}
                    >
                      {t("createModal.cancelButton.label")}
                    </Button>
                  }
                  submit={
                    <Button
                      disabled={isSubmitting || !isValid || !dirty}
                      icon={isSubmitting ? IconLoader : undefined}
                      onClick={submitForm}
                    >
                      {t("createModal.submitButton.label")}
                    </Button>
                  }
                />
              </Modal.Footer>
            </Form>
          )}
        </Formik>
      </Modal.Content>
    </Modal>
  );
}
